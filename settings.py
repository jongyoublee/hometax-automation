import os
from pathlib import Path

HOMETAX_URL = (
    "https://hometax.go.kr/websquare/websquare.html"
    "?w2xPath=/ui/pp/index_pp.xml&menuCd=index3"
)
LOGIN_SELECTOR = "#mf_txppWframe_loginboxFrame_anchor22"
WAIT_SECONDS = 30
PROFILE_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "hometax-chrome-profile"

HOMETAX_ORIGINS = (
    "https://hometax.go.kr",
    "https://www.hometax.go.kr",
)

SITE_PERMISSIONS = (
    "geolocation",
    "notifications",
    "clipboardReadWrite",
    "clipboardSanitizedWrite",
    "videoCapture",
    "audioCapture",
    "idleDetection",
    "windowManagement",
    "localFonts",
    "sensors",
    "displayCapture",
)

CHROME_ARGUMENTS = (
    "--start-maximized",
    "--use-fake-ui-for-media-stream",
    "--no-first-run",
    "--no-default-browser-check",
)

CHROME_PREFS = {
    "profile.default_content_setting_values.notifications": 1,
    "profile.default_content_setting_values.geolocation": 1,
    "profile.default_content_setting_values.media_stream_mic": 1,
    "profile.default_content_setting_values.media_stream_camera": 1,
    "profile.default_content_setting_values.automatic_downloads": 1,
    "profile.default_content_setting_values.clipboard": 1,
    "profile.default_content_setting_values.protocol_handlers": 1,
    "download.prompt_for_download": False,
    "credentials_enable_service": False,
    "profile.password_manager_enabled": False,
}
