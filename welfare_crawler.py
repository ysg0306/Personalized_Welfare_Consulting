from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time


URL = "https://www.bokjiro.go.kr"
SEARCH_WORD = "청년"


options = Options()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=options)


try:

    print("복지로 접속 중...")

    driver.get(URL)

    time.sleep(5)


    # 검색창 찾기

    inputs = driver.find_elements(
        By.CSS_SELECTOR,
        "input.cl-text"
    )

    visible_inputs = [
        x for x in inputs
        if x.is_displayed() and x.is_enabled()
    ]


    if not visible_inputs:

        print("검색창을 찾지 못했습니다.")

        driver.quit()

        exit()


    search = visible_inputs[0]


    # 검색

    driver.execute_script(
        "arguments[0].click();",
        search
    )

    search.send_keys(SEARCH_WORD)

    search.send_keys(Keys.ENTER)


    print(
        f"'{SEARCH_WORD}' 검색 중..."
    )

    time.sleep(7)


    print("\n현재 주소:")
    print(driver.current_url)

    print("\n페이지 제목:")
    print(driver.title)


    # ==================================
    # 페이지 전체 텍스트 가져오기
    # ==================================

    print("\n페이지 텍스트 분석 중...")


    body_text = driver.find_element(
        By.TAG_NAME,
        "body"
    ).text


    print("\n========== 검색 결과 텍스트 ==========\n")

    print(body_text[:10000])


    # ==================================
    # HTML 저장
    # ==================================

    with open(
        "search_result.html",
        "w",
        encoding="utf-8"
    ) as f:

        f.write(driver.page_source)


    print(
        "\nsearch_result.html 저장 완료"
    )


finally:

    time.sleep(2)

    driver.quit()

    print("\n크롤러 종료")