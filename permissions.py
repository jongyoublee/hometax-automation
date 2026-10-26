import os
import socket
import subprocess
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options


def ensure_magicline_running() -> None:
    """PC에 설치된 MagicLine4NX 보안 프로세스가 꺼져 있으면 자동으로 실행합니다."""
    candidates = [
        Path(r"C:\Program Files (x86)\DreamSecurity\MagicLine4NX\MagicLine4NX.exe"),
        Path(r"C:\Program Files\DreamSecurity\MagicLine4NX\MagicLine4NX.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "DreamSecurity" / "MagicLine4NX" / "MagicLine4NX.exe",
    ]

    for exe in candidates:
        if exe.exists():
            try:
                output = subprocess.check_output(
                    ["tasklist", "/FI", "IMAGENAME eq MagicLine4NX.exe"],
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )
                if "MagicLine4NX.exe" not in output:
                    subprocess.Popen([str(exe)])
                    time.sleep(1)
            except Exception:
                try:
                    subprocess.Popen([str(exe)])
                except Exception:
                    pass
            break


def find_chrome_executable() -> str:
    """시스템에 설치된 Chrome 실행 파일 경로를 탐색합니다."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return "chrome.exe"


def is_port_open(host: str = "127.0.0.1", port: int = 9222) -> bool:
    """디버깅 포트가 열려 있는지 확인합니다."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def ensure_chrome_running(port: int = 9222) -> None:
    """디버깅 크롬이 켜져 있지 않으면 start_chrome.bat을 실행합니다."""
    if is_port_open(port=port):
        return

    bat_path = Path(__file__).resolve().parent / "start_chrome.bat"
    if bat_path.exists():
        subprocess.Popen([str(bat_path)], shell=True)
    else:
        chrome_exe = find_chrome_executable()
        temp_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ChromeTEMP"
        subprocess.Popen([
            chrome_exe,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={temp_dir}",
            "--allow-insecure-localhost",
            "--ignore-certificate-errors",
            "https://hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index_pp.xml&menuCd=index3",
        ])

    for _ in range(30):
        if is_port_open(port=port):
            return
        time.sleep(0.3)

    raise RuntimeError(
        f"디버깅 크롬(포트 {port})이 켜져 있지 않습니다.\n"
        f"먼저 start_chrome.bat 을 실행해주세요."
    )


def grant_site_permissions(
    driver: webdriver.Chrome,
    origins: tuple[str, ...],
    site_permissions: tuple[str, ...],
) -> None:
    """CDP를 통해 홈택스 도메인에 브라우저 권한을 일괄 허용합니다."""
    for origin in origins:
        try:
            driver.execute_cdp_cmd(
                "Browser.grantPermissions",
                {"origin": origin, "permissions": list(site_permissions)},
            )
        except WebDriverException:
            for permission in site_permissions:
                try:
                    driver.execute_cdp_cmd(
                        "Browser.grantPermissions",
                        {"origin": origin, "permissions": [permission]},
                    )
                except WebDriverException:
                    continue


def hide_automation_flags(driver: webdriver.Chrome) -> None:
    """CDP 스크립트를 주입하여 navigator.webdriver 등 봇 식별 태그를 삭제합니다."""
    stealth_js = """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        window.navigator.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };
    """
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": stealth_js},
        )
    except Exception:
        pass


def create_driver(
    debug_port: int,
    origins: tuple[str, ...],
    site_permissions: tuple[str, ...],
) -> webdriver.Chrome:
    """실행 중인 디버깅 크롬에 연결하고 기본 설정을 적용합니다."""
    ensure_magicline_running()
    ensure_chrome_running(port=debug_port)

    options = Options()
    options.page_load_strategy = "eager"
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
    driver = webdriver.Chrome(options=options)

    hide_automation_flags(driver)
    grant_site_permissions(driver, origins, site_permissions)
    return driver
