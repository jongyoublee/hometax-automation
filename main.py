import sys
import threading
import time
from pathlib import Path

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoAlertPresentException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import settings
from permissions import create_driver, ensure_magicline_running


def dismiss_alert(driver: WebDriver) -> None:
    try:
        driver.switch_to.alert.dismiss()
    except NoAlertPresentException:
        pass


def close_popups(driver: WebDriver, main_handle: str) -> None:
    dismiss_alert(driver)

    for handle in list(driver.window_handles):
        if handle == main_handle:
            continue
        try:
            driver.switch_to.window(handle)
            driver.close()
        except WebDriverException:
            continue

    remaining = driver.window_handles
    target = main_handle if main_handle in remaining else remaining[0]
    driver.switch_to.window(target)
    driver.switch_to.default_content()
    dismiss_alert(driver)


def try_click(driver: WebDriver, css: str) -> bool:
    elements = driver.find_elements(By.CSS_SELECTOR, css)
    if not elements:
        return False

    element = elements[0]
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    try:
        element.click()
    except (ElementClickInterceptedException, StaleElementReferenceException):
        driver.execute_script("arguments[0].click();", element)
    return True


def try_click_in_tree(driver: WebDriver, css: str) -> bool:
    if try_click(driver, css):
        return True

    frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
    for index in range(len(frames)):
        frames = driver.find_elements(By.CSS_SELECTOR, "iframe, frame")
        if index >= len(frames):
            break
        try:
            driver.switch_to.frame(frames[index])
        except Exception:
            continue
        found = try_click_in_tree(driver, css)
        if found:
            return True
        driver.switch_to.parent_frame()
    return False


def click_selector(
    driver: WebDriver, css: str, timeout: int, main_handle: str
) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        close_popups(driver, main_handle)
        if try_click_in_tree(driver, css):
            return
        time.sleep(0.4)

    raise TimeoutException(f"요소를 찾지 못했습니다: {css}")


def main() -> None:
    print("[1/5] 브라우저 연결 및 프로필 로딩 중...")
    driver = create_driver(
        arguments=settings.CHROME_ARGUMENTS,
        prefs=settings.CHROME_PREFS,
        profile_dir=settings.PROFILE_DIR,
        origins=settings.HOMETAX_ORIGINS,
        site_permissions=settings.SITE_PERMISSIONS,
        url=settings.HOMETAX_URL,
        debug_port=settings.DEBUG_PORT,
    )
    try:
        print("[2/5] 홈택스 페이지 확인 중...")
        if "hometax.go.kr" not in driver.current_url:
            driver.get(settings.HOMETAX_URL)
        
        main_handle = driver.current_window_handle

        print("[3/5] 팝업창 정리 및 로그인 버튼 탐색 중...")
        close_popups(driver, main_handle)
        click_selector(
            driver,
            settings.LOGIN_SELECTOR,
            settings.WAIT_SECONDS,
            main_handle,
        )
        close_popups(driver, main_handle)
        print(f"[4/5] 1차 로그인 버튼 클릭 완료! ({settings.LOGIN_SELECTOR})")

        # 로그인 버튼 클릭 후 화면 로딩 대기 (5초)
        print("로그인 페이지 로딩 대기 중 (5초)...")
        time.sleep(5)

        # 인증서 버튼 클릭 전 보안프로그램(MagicLine4NX) 실행 여부 재확인
        print("[5/5] 보안프로그램 실행 상태 재확인 중...")
        ensure_magicline_running()

        print(f"인증서 버튼({settings.CERT_LOGIN_SELECTOR}) 클릭 시도 중...")
        click_selector(
            driver,
            settings.CERT_LOGIN_SELECTOR,
            settings.WAIT_SECONDS,
            main_handle,
        )
        close_popups(driver, main_handle)
        print(f"인증서 버튼 클릭 완료! ({settings.CERT_LOGIN_SELECTOR})")

        stop_watch = threading.Event()

        def watch_popups() -> None:
            while not stop_watch.wait(0.5):
                try:
                    close_popups(driver, main_handle)
                except WebDriverException:
                    continue

        watcher = threading.Thread(target=watch_popups, daemon=True)
        watcher.start()
        try:
            input("브라우저를 닫으려면 Enter를 누르세요...")
        finally:
            stop_watch.set()
    finally:
        driver.quit()


if __name__ == "__main__":
    main()

