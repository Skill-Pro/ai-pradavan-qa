import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

# ======= Фикстура браузера =======
@pytest.fixture
def driver():
    driver = webdriver.Chrome()
    driver.maximize_window()
    yield driver
    driver.quit()

# ======= Хелпер для входа =======
def login(driver, email, password):
    driver.get("https://aipradavan.city-innovation.kz/")

    # Клик по ссылке "Войти"
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[text()='Войти']"))
    ).click()

    # Ввод email и пароля
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "email"))).send_keys(email)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "password"))).send_keys(password)

    # Клик по кнопке "Войти"
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and text()='Войти']"))
    ).click()

    time.sleep(2)

# ======= Позитивный тест =======
def test_login_success(driver):
    login(driver, "zangar.zhunisbekov@gmail.com", "zangar1224")
    assert "dashboard" in driver.current_url or "Выйти" in driver.page_source

# ======= Неверный пароль =======
def test_login_invalid_password(driver):
    login(driver, "zangar.zhunisbekov@gmail.com", "wrongpassword")
    assert "Неверный" in driver.page_source or "ошибка" in driver.page_source.lower()

# ======= Неверный email =======
def test_login_invalid_email(driver):
    login(driver, "fake.email@example.com", "zangar1224")
    assert "Неверный" in driver.page_source or "ошибка" in driver.page_source.lower()

# ======= Пустые поля =======
def test_login_empty_fields(driver):
    login(driver, "", "")
    assert "обязательное" in driver.page_source.lower() or "required" in driver.page_source.lower()

# ======= Email без @ =======
def test_login_invalid_email_format(driver):
    login(driver, "invalidemail", "zangar1224")
    assert "email" in driver.page_source.lower() or "неверный формат" in driver.page_source.lower()

# ======= Автоматический скриншот при падении =======
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    result = outcome.get_result()

    if result.failed and "driver" in item.fixturenames:
        driver = item.funcargs["driver"]
        if not os.path.exists("screenshots"):
            os.mkdir("screenshots")
        screenshot_path = f"screenshots/error_{item.name}_{int(time.time())}.png"
        driver.save_screenshot(screenshot_path)
        print(f"\n📸 Скриншот сохранён: {screenshot_path}")
