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
from permissions import create_driver


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
    driver = create_driver(
        arguments=settings.CHROME_ARGUMENTS,
        prefs=settings.CHROME_PREFS,
        profile_dir=settings.PROFILE_DIR,
        origins=settings.HOMETAX_ORIGINS,
        site_permissions=settings.SITE_PERMISSIONS,
    )
    try:
        driver.get(settings.HOMETAX_URL)
        main_handle = driver.current_window_handle
        close_popups(driver, main_handle)
        click_selector(
            driver,
            settings.LOGIN_SELECTOR,
            settings.WAIT_SECONDS,
            main_handle,
        )
        close_popups(driver, main_handle)
        print(f"클릭 완료: {settings.LOGIN_SELECTOR}")

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
