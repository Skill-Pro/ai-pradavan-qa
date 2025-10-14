import os
import pytest
import requests
import uuid
from pytest_html import extras
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ===============================
# 🔹 Настройки базового URL
# ===============================
BASE_URL = "https://backend-test-service.city-innovation.kz"
USER_EMAIL = "zangar.zhunisbekov@gmail.com"
USER_PASSWORD = "zangar1224"


# ===============================
# 🔹 Название HTML отчёта
# ===============================
def pytest_html_report_title(report):
    report.title = "Отчёт по тестированию (UI + API)"


# ===============================
# 🔹 Добавляем в отчёт ответы API и скриншоты UI
# ===============================
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()

    if rep.when != "call":
        return

    rep.extra = getattr(rep, "extra", [])

    # Добавляем тело ответа API (если есть)
    response_info = getattr(item, "response_info", None)
    if response_info:
        rep.extra.append(extras.text(response_info, name="API Response"))
        rep.sections.append(("api response", response_info))

    # Скриншот для UI-тестов при падении
    if rep.failed:
        driver = item.funcargs.get("driver", None)
        if driver:
            screenshot_dir = "screenshots"
            os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_path = os.path.join(screenshot_dir, f"{item.name}.png")
            driver.save_screenshot(screenshot_path)
            rep.extra.append(extras.image(screenshot_path))


# ===============================
# 🔹 Фикстура: WebDriver для UI тестов
# ===============================
@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless")  # включить при CI
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    yield driver
    driver.quit()


# ===============================
# 🔹 Фикстура: Авторизация существующего пользователя
# ===============================
@pytest.fixture(scope="session")
def auth_headers():
    """
    Получает access_token через /api/v1/auth/login и возвращает заголовки.
    Используется во всех API тестах для авторизованных запросов.
    """
    login_data = {
        "grant_type": "password",
        "username": USER_EMAIL,
        "password": USER_PASSWORD,
        "scope": "",
        "client_id": "",
        "client_secret": ""
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data=login_data,
        headers={"accept": "application/json"}
    )

    assert response.status_code == 200, f"Ошибка авторизации: {response.text}"

    token_data = response.json()
    access_token = token_data.get("access_token")
    assert access_token, f"❌ Токен не найден в ответе: {response.text}"

    return {
        "accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }


# ===============================
# 🔹 Фикстура: Регистрация нового пользователя (для тестов с чистыми аккаунтами)
# ===============================
@pytest.fixture(scope="function")
def new_user_headers():
    """
    Создает нового пользователя с уникальным email, возвращает access_token.
    Используется в тестах, где нужен "чистый" аккаунт без ассистентов.
    """
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    register_data = {
        "email": unique_email,
        "phone_number": "+7700" + str(uuid.uuid4().int)[:7],
        "first_name": "Test",
        "last_name": "User",
        "password": "TestPassword123!",
        "role": "user",
        "referral_code": ""
    }

    response = requests.post(
        f"{BASE_URL}/api/v1/auth/register",
        json=register_data,
        headers={"accept": "application/json", "Content-Type": "application/json"}
    )

    assert response.status_code == 200, f"❌ Ошибка регистрации: {response.text}"

    token_data = response.json()
    access_token = token_data.get("access_token")
    assert access_token, f"❌ access_token не найден в ответе: {response.text}"

    return {
        "accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
