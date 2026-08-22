import argparse
import json
import os
import time
from typing import Any

import requests
from db_manager import (
    policy_transaction,
)


BASE_URL = "https://api.odcloud.kr/api"
LIST_ENDPOINT = "/gov24/v3/serviceList"
DETAIL_ENDPOINT = "/gov24/v3/serviceDetail"


def request_api(
    endpoint: str,
    service_key: str,
    params: dict[str, Any],
    session: requests.Session,
    retries: int = 3,
) -> dict[str, Any]:
    """행정안전부 API를 호출하고 JSON 응답을 반환한다."""
    request_params = {**params, "serviceKey": service_key, "returnType": "JSON"}
    url = f"{BASE_URL}{endpoint}"

    for attempt in range(retries):
        try:
            response = session.get(url, params=request_params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("API 응답이 JSON 객체가 아닙니다.")
            return payload
        except (requests.RequestException, ValueError):
            if attempt == retries - 1:
                raise
            time.sleep(2**attempt)

    raise RuntimeError("API 요청이 완료되지 않았습니다.")


def records_from_response(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """API 응답의 data가 목록 또는 단일 객체인 경우 모두 목록으로 변환한다."""
    data = payload.get("data", payload)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def values_for_keys(value: Any, keys: set[str]) -> list[str]:
    """중첩된 API 응답에서 지정한 키의 값을 문자열로 수집한다."""
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys and item not in (None, "", []):
                text = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
                if text not in found:
                    found.append(text.strip())
            else:
                found.extend(values_for_keys(item, keys))
    elif isinstance(value, list):
        for item in value:
            found.extend(values_for_keys(item, keys))
    return [item for item in found if item]


def first_value(value: Any, keys: set[str], default: str = "") -> str:
    values = values_for_keys(value, keys)
    return values[0] if values else default


def join_values(value: Any, keys: set[str]) -> str:
    return "\n".join(values_for_keys(value, keys))


def fetch_service_list(
    service_key: str,
    session: requests.Session,
    page_size: int,
) -> list[dict[str, Any]]:
    services: list[dict[str, Any]] = []
    page = 1

    while True:
        payload = request_api(
            LIST_ENDPOINT,
            service_key,
            {"page": page, "perPage": page_size},
            session,
        )
        page_services = records_from_response(payload)
        if not page_services:
            break
        services.extend(page_services)
        total_count = payload.get("totalCount")
        print(f"목록 {len(services)}개 수집 (페이지 {page})")
        if len(page_services) < page_size or (
            isinstance(total_count, int) and len(services) >= total_count
        ):
            break
        page += 1

    return services


def normalize_service(
    service: dict[str, Any],
    detail: dict[str, Any],
) -> dict[str, str]:
    service_data = {**service, **detail}
    service_id = first_value(
        service_data,
        {"서비스ID", "서비스아이디", "serviceId", "serviceID", "id"},
    )
    title = first_value(service_data, {"서비스명", "서비스명칭", "title", "name"})
    category = first_value(
        service_data,
        {"서비스분야", "서비스분류", "category", "분야", "카테고리"},
    )
    content = join_values(
        service_data,
        {"서비스목적", "서비스내용", "주요내용", "지원내용", "content", "description"},
    )
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
    with requests.Session() as session:
        services = fetch_service_list(service_key, session, page_size)
        results: list[dict[str, Any]] = []
        processed_ids: set[str] = set()

        with policy_transaction() as transaction:
            service_ids = [
                first_value(
                    service,
                    {"서비스ID", "서비스아이디", "serviceId", "serviceID", "id"},
                )
                for service in services
            ]
            existing_ids = transaction.get_existing_policy_ids(service_ids)
            print(f"기존 저장 혜택 {len(existing_ids)}개: 상세 API 요청에서 제외")

            for index, service in enumerate(services, start=1):
                service_id = first_value(
                    service,
                    {"서비스ID", "서비스아이디", "serviceId", "serviceID", "id"},
                )
                if not service_id:
                    print(f"[{index}/{len(services)}] ID 없음: 건너뜀")
                    continue
                if service_id in processed_ids:
                    print(f"[{index}/{len(services)}] {service_id} 목록 중복: 건너뜀")
                    continue
                processed_ids.add(service_id)
                if service_id in existing_ids:
                    print(f"[{index}/{len(services)}] {service_id} 이미 저장됨: 건너뜀")
                    continue

                try:
                    detail = request_api(
                        DETAIL_ENDPOINT, service_key, {"serviceId": service_id}, session
                    )
                    normalized = normalize_service(service, detail)
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
                    print(f"[{index}/{len(services)}] {service_id} 오류: {error}")
                time.sleep(delay)

            if commit:
                transaction.commit()
                print("테스트 완료: DB 트랜잭션을 커밋했습니다.")
            else:
                # 실제 DB 사용으로 고정할 때는 아래 rollback 분기를 제거하고
                # transaction.commit()을 호출하면 됩니다. 현재는 기본 테스트 보호 장치입니다.
                transaction.rollback()
                print("테스트 모드: DB 트랜잭션을 롤백했습니다. 실제 데이터는 변경되지 않았습니다.")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="행정안전부 공공서비스 혜택 수집")
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--delay", type=float, default=0.5)
    # 기본값은 테스트용 롤백입니다. 실제 DB에 반영할 때만 --commit을 추가하세요.
    # 항상 실제 저장을 사용하려면 이 줄의 default=False를 default=True로 바꾸면 됩니다.
    parser.add_argument("--commit", action="store_true", default=False)
    args = parser.parse_args()

    service_key = os.getenv("GOV24_SERVICE_KEY")
    if not service_key:
        raise SystemExit(
            "GOV24_SERVICE_KEY 환경변수가 없습니다. "
            "발급받은 행정안전부 API 인증키를 설정한 뒤 실행하세요."
        )
    if args.page_size < 1 or args.delay < 0:
        raise SystemExit("--page-size는 1 이상, --delay는 0 이상이어야 합니다.")

    data = collect_services(service_key, args.delay, args.page_size, commit=args.commit)
    print(f"수집 및 DB 처리 완료: {len(data)}개")


if __name__ == "__main__":
    main()
