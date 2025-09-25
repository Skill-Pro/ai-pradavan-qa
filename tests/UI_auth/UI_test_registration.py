import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


@pytest.fixture
def driver():
    """Инициализация браузера."""
    options = Options()
    options.add_argument("--start-maximized")
    drv = webdriver.Chrome(service=Service(), options=options)
    yield drv
    drv.quit()


def go_to_registration(driver):
    """Переход на страницу регистрации."""
    driver.get("https://test-frontik.city-innovation.kz/")
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Регистрация')]"))
    ).click()


def fill_registration_form(driver, email, password, phone):
    """Заполнение формы регистрации."""
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "email"))
    )
    driver.find_element(By.ID, "email").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.ID, "phone_number").send_keys(phone)

    terms_checkbox = driver.find_element(By.ID, "terms")
    driver.execute_script("arguments[0].click();", terms_checkbox)

    driver.find_element(By.XPATH, "//button[contains(text(), 'Зарегистрироваться')]").click()


def test_successful_registration(driver):
    """Проверка успешной регистрации."""
    go_to_registration(driver)
    fill_registration_form(driver, "new_user123@example.com", "pass12345", "+77021234567")
    WebDriverWait(driver, 10).until(EC.url_contains("profile"))
    assert "profile" in driver.current_url


def test_registration_with_existing_email(driver):
    """Регистрация с уже существующим email."""
    go_to_registration(driver)
    fill_registration_form(driver, "zangar.zhunisbekov@gmail.com", "pass12345", "+77021234567")
    error_text = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CLASS_NAME, "error-message"))
    ).text
    assert "Email уже зарегистрирован" in error_text



def test_registration_with_empty_fields(driver):
    """Регистрация с пустыми полями."""
    go_to_registration(driver)
    driver.find_element(By.XPATH, "//button[contains(text(), 'Зарегистрироваться')]").click()
    errors = driver.find_elements(By.CLASS_NAME, "error-message")
    assert len(errors) > 0
