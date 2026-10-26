HOMETAX_URL = (
    "https://hometax.go.kr/websquare/websquare.html"
    "?w2xPath=/ui/pp/index_pp.xml&menuCd=index3"
)
LOGIN_SELECTOR = "#mf_txppWframe_loginboxFrame_anchor22"
CERT_LOGIN_SELECTOR = "#MSG_TS703"
WAIT_SECONDS = 30
DEBUG_PORT = 9222

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
