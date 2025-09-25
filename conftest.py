# conftest.py
import os
import pytest
from pytest_html import extras
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def pytest_html_report_title(report):
    report.title = "Отчёт по тестированию (UI + API)"

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()

    if rep.when != "call":
        return

    rep.extra = getattr(rep, "extra", [])

    # 🔹 Добавляем API Response и в "Extra", и в "Captured log"
    response_info = getattr(item, "response_info", None)
    if response_info:
        # В "Links"
        rep.extra.append(extras.text(response_info, name="API Response"))
        # В основной лог (чтобы не было пусто «No log output captured»)
        rep.sections.append(("api response", response_info))

    # 🔹 Скриншот для UI-тестов
    if rep.failed:
        driver = item.funcargs.get("driver", None)
        if driver:
            screenshot_dir = "/screenshots"
            os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshot_dir, f"{item.name}.png")
            driver.save_screenshot(screenshot_path)
            rep.extra.append(extras.image(screenshot_path))

@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    yield driver
    driver.quit()
