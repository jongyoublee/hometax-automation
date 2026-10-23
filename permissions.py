import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options


def kill_zombie_debugger_process(port: int = 9222) -> None:
    """사용자의 일반 크롬은 절대 건드리지 않고, 9222 포트를 잡고 있는 이전 디버거 프로세스만 정리합니다."""
    try:
        output = subprocess.check_output(
            ["netstat", "-ano"],
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        for line in output.splitlines():
            if f":{port} " in line and "LISTENING" in line:
                parts = line.strip().split()
                pid = parts[-1]
                if pid.isdigit() and int(pid) > 0:
                    subprocess.run(
                        ["taskkill", "/F", "/PID", pid],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                    )
                    time.sleep(0.5)
    except Exception:
        pass


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


def get_active_profile_name(user_data_dir: Path) -> str:
    """실제 사용 중인 크롬 프로필(Default, Profile 1 등)의 이름을 탐색합니다."""
    local_state_file = user_data_dir / "Local State"
    if local_state_file.exists():
        try:
            with open(local_state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                last_used = data.get("profile", {}).get("last_used")
                if last_used and (user_data_dir / last_used).exists():
                    return last_used
        except Exception:
            pass
    return "Default"


def sync_chrome_data(target_profile_dir: Path) -> str:
    """실제 활성 프로필 데이터를 덮어써서 게스트 모드 진입을 차단합니다."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return "Default"

    src_user_data = Path(local_app_data) / "Google" / "Chrome" / "User Data"
    if not src_user_data.exists():
        return "Default"

    profile_name = get_active_profile_name(src_user_data)

    src_local_state = src_user_data / "Local State"
    dst_local_state = target_profile_dir / "Local State"
    if src_local_state.exists():
        try:
            shutil.copy2(src_local_state, dst_local_state)
        except Exception:
            pass

    src_prof = src_user_data / profile_name
    dst_prof = target_profile_dir / profile_name
    dst_prof.mkdir(parents=True, exist_ok=True)

    targets = [
        ("Extensions", True),
        ("Local Extension Settings", True),
        ("Preferences", False),
        ("Secure Preferences", False),
    ]
    for name, is_dir in targets:
        src = src_prof / name
        dst = dst_prof / name
        if not src.exists():
            continue
        try:
            if is_dir:
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
        except Exception:
            continue

    return profile_name


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
    """CDP 스크립트를 주입하여 navigator.webdriver 등 봇 식별 태그를 원천 삭제합니다."""
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


def launch_chrome_debugger(
    profile_dir: Path,
    arguments: tuple[str, ...],
    url: str = "",
    port: int = 9222,
) -> None:
    """독립된 새 창으로 디버깅 Chrome을 실행합니다."""
    kill_zombie_debugger_process(port=port)

    profile_dir.mkdir(parents=True, exist_ok=True)
    active_profile = sync_chrome_data(profile_dir)

    chrome_path = find_chrome_executable()
    cmd = [
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        f"--profile-directory={active_profile}",
    ] + list(arguments)

    if url:
        cmd.append(url)

    subprocess.Popen(cmd)

    for _ in range(30):
        if is_port_open(port=port):
            return
        time.sleep(0.3)

    raise RuntimeError("Chrome 디버깅 포트(9222) 열기에 실패했습니다.")


def create_driver(
    arguments: tuple[str, ...],
    prefs: dict,
    profile_dir: Path,
    origins: tuple[str, ...],
    site_permissions: tuple[str, ...],
    url: str = "",
    debug_port: int = 9222,
) -> webdriver.Chrome:
    """보안 프로그램 로컬 통신을 강제 허용하고 Chrome에 연결합니다."""
    ensure_magicline_running()
    launch_chrome_debugger(profile_dir, arguments, url=url, port=debug_port)

    options = Options()
    # 보안 프로그램 로컬호스트 통신 강제 허용 플래그
    options.add_argument("--allow-insecure-localhost")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-running-insecure-content")

    for arg in arguments:
        options.add_argument(arg)

    options.page_load_strategy = "eager"
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
    driver = webdriver.Chrome(options=options)

    hide_automation_flags(driver)
    grant_site_permissions(driver, origins, site_permissions)
    return driver
