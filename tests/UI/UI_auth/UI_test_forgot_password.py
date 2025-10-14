import os
import re
import pytest
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from mailslurp_client import Configuration, ApiClient, WaitForControllerApi

# 🔹 Загрузка переменных окружения
load_dotenv()

MAILSLURP_API_KEY = os.getenv("MAILSLURP_API_KEY")
REGISTERED_EMAIL = os.getenv("REGISTERED_EMAIL")
INBOX_ID = os.getenv("INBOX_ID")
NEW_PASSWORD = os.getenv("NEW_PASSWORD")

# 🔸 Проверка переменных окружения
assert MAILSLURP_API_KEY, "MAILSLURP_API_KEY not set in .env"
assert REGISTERED_EMAIL, "REGISTERED_EMAIL not set in .env"
assert INBOX_ID, "INBOX_ID not set in .env"
assert NEW_PASSWORD, "NEW_PASSWORD not set in .env"

# 🔹 Фикстура браузера
@pytest.fixture
def browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    yield driver
    driver.quit()

# 🔹 Вспомогательные функции
def click_element(wait, by, value):
    wait.until(EC.element_to_be_clickable((by, value))).click()

def enter_text(wait, by, value, text):
    element = wait.until(EC.presence_of_element_located((by, value)))
    element.clear()
    element.send_keys(text)

def extract_link_from_email(body):
    match = re.search(r'href="([^"]+)"', body)
    return match.group(1) if match else None

# 🔹 Тест восстановления пароля
def test_forgot_password_flow(browser):
    wait = WebDriverWait(browser, 10)

    # Настройка MailSlurp
    configuration = Configuration()
    configuration.api_key["x-api-key"] = MAILSLURP_API_KEY
    api_client = ApiClient(configuration)
    wait_controller = WaitForControllerApi(api_client)

    # 1. Открыть сайт
    browser.get("https://test-frontik.city-innovation.kz/")

    # 2. Нажать "Войти"
    click_element(wait, By.XPATH, "//a[text()='Войти']")

    # 3. Нажать "Забыли пароль?"
    click_element(wait, By.XPATH, "//a[contains(text(),'Забыли пароль')]")

    # 4. Ввести email
    enter_text(wait, By.ID, "email", REGISTERED_EMAIL)

    # 5. Нажать "Восстановить"
    click_element(wait, By.XPATH, "//button[contains(text(),'Восстановить')]")

    # 6. Получить письмо MailSlurp
    email = wait_controller.wait_for_latest_email(
        inbox_id=INBOX_ID,
        timeout=30000,
        unread_only=True
    )

    # 7. Извлечь ссылку на сброс пароля
    reset_link = extract_link_from_email(email.body)
    assert reset_link, "Ссылка для сброса пароля не найдена в письме"
    print("🔗 Ссылка для сброса пароля:", reset_link)

    # 8. Перейти по ссылке сброса
    browser.get(reset_link)

    # 9. Ввести новый пароль и подтверждение
    enter_text(wait, By.ID, "password", NEW_PASSWORD)
    enter_text(wait, By.ID, "confirmPassword", NEW_PASSWORD)

    # 10. Подтвердить смену пароля
    click_element(wait, By.XPATH, "//button[contains(text(),'Сменить')]")

    # 11. Проверить успешное сообщение
    success_msg = wait.until(EC.visibility_of_element_located(
        (By.XPATH, "//div[contains(text(),'успешно')]")
    ))
    assert "успешно" in success_msg.text.lower(), "Пароль не был успешно изменён"
