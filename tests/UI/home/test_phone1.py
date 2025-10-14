import pytest
import time
from seleniumwire import webdriver
from selenium.webdriver.common.by import By


@pytest.fixture
def driver():
    """Фикстура для запуска и закрытия браузера"""
    options = {
        'disable_encoding': True
    }
    driver = webdriver.Chrome(seleniumwire_options=options)
    driver.maximize_window()
    yield driver
    driver.quit()


def test_phone_request_status_200(driver):
    driver.get("https://aipradavan.city-innovation.kz/")
    time.sleep(2)  # Ждем загрузки страницы

    # Вводим номер телефона
    phone_input = driver.find_element(By.CSS_SELECTOR, "input[type='tel']")
    phone_input.clear()
    phone_input.send_keys("+7 (777) 777-77-77")

    # Кликаем на кнопку "Запросить консультацию"
    submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Запросить консультацию')]")
    submit_btn.click()

    # Ждем отправки запроса
    time.sleep(3)

    # Проверяем, что среди запросов есть POST с кодом 200
    found_200 = False
    for request in driver.requests:
        if request.response:
            # фильтруем, чтобы не брать все подряд, а только POST
            if request.method == "POST" and request.response.status_code == 200:
                print(f"[OK] Запрос {request.url} вернул 200")
                found_200 = True
                break

    assert found_200, "Нет POST-запроса с кодом 200"
