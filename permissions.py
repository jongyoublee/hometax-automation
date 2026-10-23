from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options


def apply_chrome_options(
    arguments: tuple[str, ...],
    prefs: dict,
    profile_dir: Path,
) -> Options:
    options = Options()
    for argument in arguments:
        options.add_argument(argument)
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_experimental_option("prefs", prefs)
    return options


def grant_site_permissions(
    driver: webdriver.Chrome,
    origins: tuple[str, ...],
    site_permissions: tuple[str, ...],
) -> None:
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


def create_driver(
    arguments: tuple[str, ...],
    prefs: dict,
    profile_dir: Path,
    origins: tuple[str, ...],
    site_permissions: tuple[str, ...],
) -> webdriver.Chrome:
    profile_dir.mkdir(parents=True, exist_ok=True)
    driver = webdriver.Chrome(
        options=apply_chrome_options(arguments, prefs, profile_dir)
    )
    grant_site_permissions(driver, origins, site_permissions)
    return driver
