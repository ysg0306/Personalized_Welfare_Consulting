import argparse
import json
import os
import time
from typing import Any

import requests
from db_manager import (
    policy_transaction,
)

# ★ 행정안전부 공공데이터 API 기본 주소
BASE_URL = "https://api.odcloud.kr/api"

# ★ 공공서비스 목록 API
LIST_ENDPOINT = "/gov24/v3/serviceList"

# ★ 특정 공공서비스의 상세정보 API
DETAIL_ENDPOINT = "/gov24/v3/serviceDetail"


def request_api(
    endpoint: str,
    service_key: str,
    params: dict[str, Any],
    session: requests.Session,
    retries: int = 3,
) -> dict[str, Any]:
    """행정안전부 API를 호출하고 JSON 응답을 반환한다."""

    # ★ API 인증키와 JSON 응답 형식을 요청 파라미터에 추가
    request_params = {
   **params, 
   "serviceKey": service_key, 
   "returnType": "JSON"
    }

    url = f"{BASE_URL}{endpoint}"

    # ★ API 요청 실패 시 최대 3번까지 재시도
    for attempt in range(retries):
        try:
       # ★ 실제 행정안전부 API 호출
            response = session.get(
      url, 
      params=request_params,
      timeout=30
       )
       # ★ 401, 404, 500 등의 HTTP 오류 확인
            response.raise_for_status()

       # ★ API 응답을 JSON 형태로 변환
            payload = response.json()

            if not isinstance(payload, dict):
                raise ValueError("API 응답이 JSON 객체가 아닙니다.")

            return payload

        except (requests.RequestException, ValueError):
            if attempt == retries - 1:
                raise

       # ★ 오류 발생 시 잠시 기다린 후 다시 요청
            time.sleep(2**attempt)

    raise RuntimeError("API 요청이 완료되지 않았습니다.")


def records_from_response(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """API 응답의 data가 목록 또는 단일 객체인 경우 모두 목록으로 변환한다."""
    data = payload.get("data", payload)
    # ★ API에서 여러 개의 데이터가 온 경우
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]

    # ★ API에서 데이터 하나만 온 경우에도 리스트 형태로 변환
    if isinstance(data, dict):
        return [data]
    return []


def values_for_keys(value: Any, keys: set[str]) -> list[str]:
    """중첩된 API 응답에서 지정한 키의 값을 문자열로 수집한다."""
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():

       # ★ 원하는 항목의 값을 찾아서 저장
            if key in keys and item not in (None, "", []):
                text = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
                if text not in found:
                    found.append(text.strip())
            else:
      # ★ 데이터가 중첩되어 있으면 내부까지 계속 탐색
                found.extend(values_for_keys(item, keys))
    elif isinstance(value, list):
        for item in value:
            found.extend(values_for_keys(item, keys))
    return [item for item in found if item]


def first_value(value: Any, keys: set[str], default: str = "") -> str:

    # ★ 지정한 키에서 첫 번째 값을 가져옴
    values = values_for_keys(value, keys)

    return values[0] if values else default


def join_values(value: Any, keys: set[str]) -> str:
    # ★ 여러 개의 값을 줄바꿈으로 합침
    return "\n".join(values_for_keys(value, keys))


def fetch_service_list(
    service_key: str,
    session: requests.Session,
    page_size: int,
) -> list[dict[str, Any]]:

    # ★ 전체 공공서비스 목록을 저장할 리스트
    services: list[dict[str, Any]] = []

    page = 1

    while True:

   # ★ 공공서비스 목록 API 호출
        payload = request_api(
            LIST_ENDPOINT,
            service_key,
            {"page": page, "perPage": page_size},
            session,
        )
        page_services = records_from_response(payload)
        if not page_services:
            break

   # ★ 현재 페이지의 서비스를 전체 목록에 추가
        services.extend(page_services)
        total_count = payload.get("totalCount")
        print(f"목록 {len(services)}개 수집 (페이지 {page})")

   # ★ 마지막 페이지인지 확인
        if len(page_services) < page_size or (
            isinstance(total_count, int) and len(services) >= total_count
        ):
            break

   # ★ 다음 페이지로 이동
        page += 1

    return services


def normalize_service(
    service: dict[str, Any],
    detail: dict[str, Any],
) -> dict[str, str]:

    # ★ 목록 API와 상세 API의 데이터를 하나로 합침
    service_data = {**service, **detail}

    # ★ 서비스 ID 추출
    service_id = first_value(
        service_data,
        {"서비스ID", "서비스아이디", "serviceId", "serviceID", "id"},
    )

    # ★ 서비스 이름 추출
    title = first_value(service_data, {"서비스명", "서비스명칭", "title", "name"})

    # ★ 서비스 분야 / 카테고리 추출
    category = first_value(
        service_data,
        {"서비스분야", "서비스분류", "category", "분야", "카테고리"},
    )
    # ★ 서비스 목적, 내용, 지원내용 등을 하나로 모음
    content = join_values(
        service_data,
        {"서비스목적", "서비스내용", "주요내용", "지원내용", "content", "description"},
    )
    # ★ DB에 저장하기 위한 형태로 데이터 정리
    return {
        "id": service_id,
        "title": title,
        "category": category,
        "content": content,
    }


def collect_services(
    service_key: str,
    delay: float,
    page_size: int,
    commit: bool = False,
) -> list[dict[str, Any]]:

    # ★ API 연결을 관리하기 위한 Session 생성
    with requests.Session() as session:

   # ★ 공공서비스 전체 목록 수집
        services = fetch_service_list(service_key, session, page_size)
        results: list[dict[str, Any]] = []

   # ★ 중복 서비스 ID 방지를 위한 집합
        processed_ids: set[str] = set()

   # ★ DB 작업을 하나의 트랜잭션으로 처리
        with policy_transaction() as transaction:

       # ★ 전체 서비스에서 ID만 추출
            service_ids = [
                first_value(
                    service,
                    {"서비스ID", "서비스아이디", "serviceId", "serviceID", "id"},
                )
                for service in services
            ]

       # ★ DB에 이미 저장된 서비스 ID 확인
            existing_ids = transaction.get_existing_policy_ids(service_ids)
            print(f"기존 저장 혜택 {len(existing_ids)}개: 상세 API 요청에서 제외")

       # ★ 서비스 하나씩 순서대로 처리
            for index, service in enumerate(services, start=1):

      # ★ 현재 서비스의 ID 추출
                service_id = first_value(
                    service,
                    {"서비스ID", "서비스아이디", "serviceId", "serviceID", "id"},
                )
      
      # ★ ID가 없는 서비스는 건너뜀
                if not service_id:
                    print(f"[{index}/{len(services)}] ID 없음: 건너뜀")
                    continue

      # ★ 목록 자체에 같은 ID가 중복되어 있으면 건너뜀
                if service_id in processed_ids:
                    print(f"[{index}/{len(services)}] {service_id} 목록 중복: 건너뜀")
                    continue
                processed_ids.add(service_id)

      # ★ 이미 DB에 있는 서비스는 상세 API를 호출하지 않음
                if service_id in existing_ids:
                    print(f"[{index}/{len(services)}] {service_id} 이미 저장됨: 건너뜀")
                    continue

                try:

          # ★ 새로운 서비스의 상세정보 API 호출
                    detail = request_api(
                        DETAIL_ENDPOINT, service_key, {"serviceId": service_id}, session
                    )

          # ★ API 데이터를 DB 저장용 데이터로 정리
                    normalized = normalize_service(service, detail)

          # ★ 정리된 데이터를 트랜잭션에 추가
                    inserted = transaction.insert_policy(
                        normalized["id"],
                        normalized["title"],
                        normalized["category"],
                        normalized["content"],
                    )
                    if inserted:
                        results.append(normalized)
                        print(f"[{index}/{len(services)}] {service_id} 트랜잭션에 추가")
                    else:
                        print(f"[{index}/{len(services)}] {service_id} 동시 저장됨: 건너뜀")
                except (requests.RequestException, ValueError) as error:

          # ★ 하나의 서비스에서 오류가 발생해도
                    # 전체 수집을 중단하지 않고 다음 서비스로 넘어감
                    print(f"[{index}/{len(services)}] {service_id} 오류: {error}")

      # ★ API 과도한 호출을 막기 위해 요청 사이에 대기
                time.sleep(delay)

       # ★ --commit 옵션이 있으면 실제 DB에 변경사항 저장
            if commit:
                transaction.commit()
                print("테스트 완료: DB 트랜잭션을 커밋했습니다.")
            else:
                # 실제 DB 사용으로 고정할 때는 아래 rollback 분기를 제거하고
                # transaction.commit()을 호출하면 됩니다. 현재는 기본 테스트 보호 장치입니다.
                transaction.rollback()
                print("테스트 모드: DB 트랜잭션을 롤백했습니다. 실제 데이터는 변경되지 않았습니다.")
    return results

# 실제 사용 예시
# def main() -> None:
#     parser = argparse.ArgumentParser(description="행정안전부 공공서비스 혜택 수집")
#     # ★ 한 번에 가져올 서비스 개수
#     parser.add_argument("--page-size", type=int, default=1000)
#     # ★ API 요청 사이의 지연시간
#     parser.add_argument("--delay", type=float, default=0.5)
#     # 기본값은 테스트용 롤백입니다. 실제 DB에 반영할 때만 --commit을 추가하세요.
#     # 항상 실제 저장을 사용하려면 이 줄의 default=False를 default=True로 바꾸면 됩니다.
#     parser.add_argument("--commit", action="store_true", default=False)
#     args = parser.parse_args()

#     # ★ 환경변수에서 행정안전부 API 인증키 가져오기
#     service_key = os.getenv("GOV24_SERVICE_KEY")

#     # ★ 인증키가 없으면 프로그램 실행 중단
#     if not service_key:
#         raise SystemExit(
#             "GOV24_SERVICE_KEY 환경변수가 없습니다. "
#             "발급받은 행정안전부 API 인증키를 설정한 뒤 실행하세요."
#         )
#     # ★ 입력값이 올바른지 검사
#     if args.page_size < 1 or args.delay < 0:
#         raise SystemExit("--page-size는 1 이상, --delay는 0 이상이어야 합니다.")

#     # ★ 실제 데이터 수집 및 DB 처리 시작
#     data = collect_services(service_key, args.delay, args.page_size, commit=args.commit)
#     print(f"수집 및 DB 처리 완료: {len(data)}개")

# # ★ 이 파일을 직접 실행했을 때 main() 실행
# if __name__ == "__main__":
#     main()
