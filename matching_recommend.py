import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from db_manager import collection, get_mysql_conn
from keybert import KeyBERT  # 한국어 키워드 추출
from kiwipiepy import Kiwi  # 한국어 형태소 분석기
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer, util
import torch

# BASE_DIR = Path.cwd()
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "raw"


def _make_keyword_embedding(data: pd.DataFrame):
    """
    복지 혜택 데이터에 키워드 임베딩값이 없는 경우 생성 후 저장하는 함수
    """
    if "keyword_embedding" not in data.columns:
        data["keyword_embedding"] = None

    if data["keyword_embedding"].notna().all():
        return

    embedding_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    kiwi = Kiwi()
    keywoerd_model = KeyBERT(model=embedding_model)

    mask = data["keyword_embedding"].isna()
    index = data[mask].index

    # 배치 처리: 모든 키워드를 한 번에 임베딩
    keyword_texts = []
    for idx in index:
        row = data.loc[idx]
        tokens = kiwi.tokenize(str(row["original_content"]))
        policy_keyword = _build_policy_keyword_features(data.loc[idx], model=keywoerd_model, tokens=tokens)
        keyword_texts.append(policy_keyword)
    
    # [수정] 판다스 칼럼을 미리 object 타입으로 변환
    # 이유: 기본 데이터 타입 상태에서 벡터(리스트)를 넣으면 판다스가 차원/길이 불일치 에러(ValueError)를 발생시킴
    data["keyword_embedding"] = data.get("keyword_embedding", None).astype(object)

    # 한 번에 배치 임베딩 수행
    embeddings = embedding_model.encode(keyword_texts)
    
    # 결과 저장
    # [수정] .loc 대신 .at 사용
    # 이유: 단일 행 인덱싱 시 .loc을 쓰면 ndarray 대입 에러가 발생하므로, 단일 셀 대입에 최적화된 .at 사용
    for idx, embedding in zip(index, embeddings):
        data.at[idx, "keyword_embedding"] = embedding.tolist()

    # DB업데이트
    conn = get_mysql_conn()
    try:
        with conn.cursor() as cursor:
            # 임시 테이블 생성
            cursor.execute("""
                CREATE TEMPORARY TABLE temp_keyword_embeddings (
                    policy_id VARCHAR(255) PRIMARY KEY,
                    keyword_embedding JSON
                )
            """)
            update_tuples = []
            for idx in index:
                row = data.loc[idx]
                p_id = str(row["policy_id"] if "policy_id" in row else str(idx))
                emb_json = json.dumps(row["keyword_embedding"])
                update_tuples.append((p_id, emb_json))

            # 임시 테이블에 일괄 삽입
            cursor.executemany("""
                INSERT INTO temp_keyword_embeddings (policy_id, keyword_embedding)
                VALUES (%s, %s)
            """, update_tuples)

            # 원본 테이블(policies)의 keyword_embedding 컬럼만 선택적 UPDATE
            cursor.execute("""
                UPDATE policies p
                JOIN temp_keyword_embeddings t ON p.policy_id = t.policy_id
                SET p.keyword_embedding = t.keyword_embedding
            """)
        conn.commit()
    finally:
        conn.close()


def _build_user_keyword_features(user_profile: Dict[str, Any]) -> str:
    """
    (사용자)키워드 기반 특징 생성 => 사용자 프로필 기반으로 가상 생성하는 함수(키워드 업데이트 필요)
    return : 사용자의 여러 키워드를 공백으로 구분하여 합친 문자열
    """
    age = int(user_profile.get("user_age", 0) or 0)
    income = int(user_profile.get("user_income", 0) or 0)
    region = str(user_profile.get("user_region", "")).strip()
    is_student = bool(user_profile.get("is_student", False))
    grade = int(user_profile.get("user_grade", 0) or 0)

    keywords = []
    if is_student:
        keywords.extend(["학생", "대학생", "등록금", "장학"])
    else:
        keywords.extend(["일반", "성인", "취업"])
    if age <= 25:
        keywords.extend(["청년", "신입생", "대학생"])
    if income <= 5:
        keywords.extend(["저소득", "소득", "중위소득"])
    if grade:
        keywords.extend([f"{grade}학년", "학년"])
    if region:
        keywords.append(region)
    # 텍스트 입력시 키워드 분석 코드 추가 예정

    user_keywords = " ".join(keywords)
    return user_keywords


def _build_user_content_features(user_profile: Dict[str, Any]) -> str:
    """
    사용자 프로필 기반으로 텍스트 표현 생성
    """
    # 1. 사용자가 직접 입력한 user_text가 있으면 1순위로 사용!
    user_text = str(user_profile.get("user_text", "")).strip()
    if user_text:
        return user_text

    # 2. 만약 입력한 텍스트가 없으면 기존 프로필 기반 문장 사용 (Fallback)
    user_keywords = _build_user_keyword_features(user_profile)
    return f"사용자 프로필 정보: {user_keywords}" if user_keywords else ""


def _build_policy_keyword_features(policy_data: pd.Series, model, tokens) -> str:
    """
    KeyBERT로 복지 혜택 본문에서 키워드를 추출하는 함수
    """
    content = str(policy_data.get("original_content", ""))
    
    if not content.strip():
        return ""

# [수정] candidates 파라미터 제거
# 이유: KeyBERT에 candidates 파라미터 전달 시 문자열 차원 에러(ValueError: too many dimensions 'str')가 발생하는 문제 방지
    keywords = model.extract_keywords(
        content, 
        keyphrase_ngram_range=(1, 2), 
        top_n=5
    )
    
    policy_keywords = " ".join([kw[0] for kw in keywords if isinstance(kw, tuple)])
    return policy_keywords


def calculate_similarity(user_data: str, policy_data: pd.DataFrame, type: str) -> float:
    """
    사용자 프로필 키워드와 복지 혜택 키워드의 유사도를 계산하는 함수
    """
# [수정] user_data 타입 안전화
# 이유: 입력값이 숫자가 들어오거나 None일 경우 model.encode()에서 에러가 나는 것을 방지하기 위해 문자열로 강제 변환
    user_str = str(user_data) if user_data is not None else ""
    if user_str == "0":
        user_str = ""

    model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    user_embedding = model.encode(user_str, convert_to_tensor=True)

    # [수정] DB 임베딩 파싱 예외 처리
    # 이유: DB에서 읽어온 임베딩 값이 JSON string 문자열로 존재할 경우 torch.tensor() 변환 시 차원 에러 발생.
    # json.loads()를 통해 float 리스트로 복원 후 텐서 변환
    raw_embeddings = policy_data[type].tolist() if type in policy_data.columns else []
    clean_embeddings = []

    for emb in raw_embeddings:
        if isinstance(emb, str):
            try:
                clean_embeddings.append(json.loads(emb))
            except Exception:
                clean_embeddings.append([0.0] * 768)
        elif isinstance(emb, list):
            clean_embeddings.append(emb)
        else:
            clean_embeddings.append([0.0] * 768)

    # 기본 예외 처리 (임베딩 데이터가 비어있을 경우)
    if not clean_embeddings:
        clean_embeddings = [[0.0] * 768 for _ in range(len(policy_data))]

    policy_embedding = torch.tensor(clean_embeddings, dtype=torch.float32, device=user_embedding.device)
    similarity = util.cos_sim(user_embedding, policy_embedding)[0]

    return similarity


def make_score(user_profile: Dict[str, Any], policy_data: pd.DataFrame, top_k=3) -> List[Dict[str, Any]]:
    """
    사용자 프로필과 복지 혜택 간의 유사도를 기반으로 점수를 계산하는 함수
    """
    _make_keyword_embedding(policy_data)

    user_keywords = _build_user_keyword_features(user_profile)
    user_content = _build_user_content_features(user_profile)
    
    keywords_similarity = calculate_similarity(user_keywords, policy_data, type="keyword_embedding")
    content_similarity = calculate_similarity(user_content, policy_data, type="text_embedding")
    
    w_kw = 0.3
    w_content = 0.7

    similarity_score = (w_kw * keywords_similarity) + (w_content * content_similarity)
    top_score, top_indices = torch.topk(similarity_score, k=min(top_k, len(policy_data)))
    return policy_data.iloc[top_indices.cpu().numpy()].assign(score=top_score.cpu().numpy()).to_dict(orient="records")