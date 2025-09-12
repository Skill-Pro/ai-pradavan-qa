import os
import pytest
import pytest_html
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 🔹 Название отчёта
def pytest_html_report_title(report):
    report.title = "Отчёт по тестированию логина"
# 🔹 Фиксация скриншота при падении теста
def pytest_runtest_makereport(item, call):
    if call.when == "call" and call.excinfo is not None:
        screenshot_dir = "screenshots"
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)

        screenshot_path = os.path.join(screenshot_dir, f"{item.name}.png")
        driver = item.funcargs.get("driver")
        if driver:
            driver.save_screenshot(screenshot_path)

        extra = getattr(item.config, "extra", [])
        extra.append(pytest_html.extras.image(screenshot_path))
        setattr(item.config, "extra", extra)

# 🔹 Фикстура браузера для тестов
@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless")  # Убери комментарий, если хочешь запуск без окна
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    yield driver
    driver.quit()
