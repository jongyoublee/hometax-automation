import time
import pyperclip
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

# 1. 브라우저 옵션 설정
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
# 네이티브 윈도우 팝업을 띄워야 하므로 headless 모드는 지원되지 않습니다.

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 20)

try:
    # 2. 홈택스 로그인 페이지 접속
    driver.get("https://www.hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index_pp.xml")
    time.sleep(3)  # 웹스퀘어 프레임워크 초기화 대기

    # 홈택스 상단 '로그인' 버튼 클릭 (화면 구성에 맞춰 셀렉터 확인 필요)
    # 직접 로그인 화면으로 들어가지 않은 경우 메인 상단 로그인 버튼 클릭
    try:
        login_btn = wait.until(EC.element_to_be_clickable((By.ID, "mf_wfm_gnb_gnbMenu_lbl_login")))
        login_btn.click()
    except Exception:
        pass  # 이미 로그인 페이지에 진입한 경우 패스

    # '공동·금융인증서' 버튼 클릭 (iframe 내부인 경우 switch_to 필요할 수 있음)
    cert_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '공동·금융인증서')]")))
    cert_btn.click()
    print("인증서 창 호출 대기 중...")

    # 3. pywinauto로 인증서 선택창(AnySign4PC / 전자서명) 제어
    app = Desktop(backend="win32")
    
    # 일반적인 공인인증서 창 타이틀 정규식 매칭
    cert_window = None
    for _ in range(15):
        try:
            cert_window = app.window(title_re=".*인증서.*|.*전자서명.*|.*AnySign.*")
            if cert_window.exists(timeout=1):
                break
        except Exception:
            time.sleep(1)

    if not cert_window or not cert_window.exists():
        raise TimeoutError("인증서 팝업창을 찾을 수 없습니다.")

    cert_window.set_focus()
    time.sleep(1)

    # 4. 인증서 위치 및 목록 선택
    # [하드디스크/이동식디스크 선택] 기본값이 하드디스크가 아닌 경우 Tab 또는 방향키로 위치 이동
    # [특정 인증서 선택]: 목록 창에서 원하는 인증서 위치로 화살표 아래(Down) 이동
    # 아래는 기본 첫 번째 인증서가 선택된 상태에서 비밀번호 입력창으로 포커스를 옮기는 방식입니다.
    
    # 5. 비밀번호 입력
    # 방법 A: 키보드 Tab 키로 비밀번호 입력 필드로 포커스 이동 (일반적인 팝업 구조 기준 2~3회 Tab)
    send_keys("{TAB}")
    send_keys("{TAB}")
    time.sleep(0.5)

    # 방법 B: 비밀번호 전송
    cert_pw = "당신의_인증서_비밀번호"  # 실제 암호로 대체 (특수문자 주의)
    
    # 키보드 보안이 물려있을 경우 send_keys 대신 클립보드 붙여넣기가 안정적일 수 있음
    pyperclip.copy(cert_pw)
    send_keys("^v")  # Ctrl + V
    time.sleep(0.5)
    
    # 확인 버튼 클릭 (엔터)
    send_keys("{ENTER}")
    print("인증서 비밀번호 입력 및 확인 전송 완료")

    # 6. 로그인 완료 후 메인화면 로딩 대기
    time.sleep(5)
    print("로그인 완료 여부 확인:", driver.current_url)

finally:
    # 작업 완료 후 브라우저 상태 유지를 위해 sleep을 주거나 제어 루틴 추가
    time.sleep(5)