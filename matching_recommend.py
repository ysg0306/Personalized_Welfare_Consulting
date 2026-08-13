from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from keybert import KeyBERT    # 한국어 키워드 추출
from kiwipiepy import Kiwi     # 한국어 형태소 분석기
from sentence_transformers import SentenceTransformer, util
import torch


# BASE_DIR = Path.cwd()
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "raw"

# DB호출로 수정 예정
def load_data(date_path: Path) -> pd.DataFrame:
   
    file_path = list(date_path.glob("*.csv"))
    if not file_path:
        raise FileNotFoundError("폴더 안에 CSV 파일이 존재하지 않습니다.")
    data = pd.read_csv(file_path[0])

    _make_keyword_embedding(data)
    return data

def _make_keyword_embedding(data: pd.DataFrame):
    """
    복지 혜택 데이터에 키워드 임베딩값이 없는 경우 생성 후 저장하는 함수
    """
    if "embedding" not in data.columns:
        data["keyword_embedding"] = None

    if data["keyword_embedding"].notna().all():
        return

    embedding_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    kiwi = Kiwi()
    keywoerd_model = KeyBERT(model=SentenceTransformer('jhgan/ko-sroberta-multitask'))
    tokens = kiwi.tokenize(data["original_content"])

    mask = data["keyword_embedding"].isna()
    index = data[mask].index

    # 배치 처리: 모든 키워드를 한 번에 임베딩
    keyword_texts = []
    for idx in index:
        policy_keyword = _build_policy_keyword_features(data.loc[idx], model=keywoerd_model, tokens=tokens)
        keyword_texts.append(policy_keyword)
    
    # 한 번에 배치 임베딩 수행
    embeddings = embedding_model.encode(keyword_texts, convert_to_tensor=True)
    
    # 결과 저장
    for idx, embedding in zip(index, embeddings):
        data.loc[idx, "embedding"] = embedding


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
    사용자 프로필 기반으로 가상 텍스트 생성
    LLM 에이전트 활용
    """
    pass


# 혜택 키워드 기반 특징 생성(미리 임베딩을 수행/ 업데이트 대비)
def _build_policy_keyword_features(policy_data: pd.Series,model,tokens) -> str:
    """
    형태소 분석으로 키워드 후보 명사 추출 후 KeyBERT로 키워드 추출하는 함수
    policy_data : 하드 필터링을 거친 복지 혜택 중 하나의 정책 데이터(Series)
    """

    # NNG: 일반 명사, NNP: 고유 명사, NNB: 의존 명사
    nouns = [token.form for token in tokens if token.tag in ['NNG', 'NNP', 'NNB']]
    # 후보 키워드 중복 제거
    candidate_keywords = list(set(nouns))

    if candidate_keywords:
        keywords = model.extract_keywords(policy_data["original_content"], candidates=candidate_keywords, keyphrase_ngram_range=(1, 2), top_n=5)
    else:
        keywords = model.extract_keywords(policy_data["original_content"], keyphrase_ngram_range=(1, 2), top_n=5)
    # KeyBERT 반환 형식 (keyword, score) 튜플에서 keyword만 추출
    policy_keywords = " ".join([kw[0] if isinstance(kw, tuple) else kw for kw in keywords])
    return policy_keywords



# 사용자 프로필 키워드기반와 복지 혜택 키워드의 유사도를 계산하는 함수
def calculate_similarity(user_data: str, policy_data : pd.DataFrame, type : str) -> float:
    """
    사용자 프로필 키워드와 복지 혜택 키워드의 유사도를 계산하는 함수
    user_data : 사용자 프로필 기반 데이터
    policy_data : 복지 혜택 데이터
    """
    model = SentenceTransformer('jhgan/ko-sroberta-multitask')
    user_embedding = model.encode(user_data, convert_to_tensor=True)

    policy_embedding = torch.tensor(policy_data[type].tolist(),dtype=torch.float32, device=user_embedding.device)
    similarity = util.cos_sim(user_embedding, policy_embedding)[0]

    return similarity


def make_score(user_profile: Dict[str, Any], policy_data: pd.DataFrame, top_k = 3) -> List[Dict[str, Any]]:
    """
    사용자 프로필과 복지 혜택 간의 유사도를 기반으로 점수를 계산하는 함수
    returns: 추천 정책 리스트 (JSON) top_k 개수만큼 반환
    """
    user_keywords = _build_user_keyword_features(user_profile)
    user_content = _build_user_content_features(user_profile)
    keywords_similarity = calculate_similarity(user_keywords, policy_data, type="keyword_embedding")
    content_similarity = calculate_similarity(user_content, policy_data, type="text_embedding")
    w_kw = 0.3
    w_content = 0.7

    similarity_score = (w_kw * keywords_similarity) + (w_content * content_similarity)
    top_score, top_indices = torch.topk(similarity_score, k=top_k)
    return policy_data.iloc[top_indices.cpu().numpy()].assign(score=top_score.cpu().numpy()).to_dict(orient="records")