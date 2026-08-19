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
        policy_keyword = _build_policy_keyword_features(model=keywoerd_model, tokens=tokens)
        keyword_texts.append(policy_keyword)
    
    data["keyword_embedding"] = data.get("keyword_embedding", None).astype(object)

    # 한 번에 배치 임베딩 수행
    embeddings = embedding_model.encode(keyword_texts)

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

    


def _build_policy_keyword_features(model, tokens) -> str:
    """
    KeyBERT로 복지 혜택 본문에서 키워드를 추출하는 함수
    """
    if not tokens:
        return ""

    # NNG: 일반 명사, NNP: 고유 명사, NNB: 의존 명사
    nouns = [token.form for token in tokens if token.tag in ["NNG", "NNP", "NNB"] and len(token.form) > 1]

    if not nouns:
        return ""
    clean_text = " ".join(nouns)
    try:
        keywords = model.extract_keywords(
            clean_text, 
            keyphrase_ngram_range=(1, 2), 
            top_n=5
        )
        return " ".join([kw[0] if isinstance(kw,tuple) else kw for kw in keywords])
    
    except Exception:
        return ""


def calculate_similarity(user_data: str, policy_data: pd.DataFrame, type: str) -> float:
    """
    사용자 프로필 키워드와 복지 혜택 키워드의 유사도를 계산하는 함수
    return : 유사도 점수
    """

    user_str = str(user_data) if user_data is not None else ""
    if user_str == "0":
        user_str = ""

    model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    user_embedding = model.encode(user_str, convert_to_tensor=True)

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


def make_score(user_profile: Dict[str, Any], user_text : List[str], policy_data: pd.DataFrame, top_k=3) -> List[Dict[str, Any]]:
    """
    사용자 프로필과 복지 혜택 간의 유사도를 기반으로 점수를 계산하는 함수
    return : 상위 복지 혜택 top_k개
    """
    _make_keyword_embedding(policy_data)

    user_keywords = _build_user_keyword_features(user_profile)
    user_content = user_text[0]
    
    keywords_similarity = calculate_similarity(user_keywords, policy_data, type="keyword_embedding")
    content_similarity = calculate_similarity(user_content, policy_data, type="text_embedding")
    
    w_kw = 0.3
    w_content = 0.7

    similarity_score = (w_kw * keywords_similarity) + (w_content * content_similarity)
    top_score, top_indices = torch.topk(similarity_score, k=min(top_k, len(policy_data)))
    return policy_data.iloc[top_indices.cpu().numpy()].assign(score=top_score.cpu().numpy()).to_dict(orient="records")