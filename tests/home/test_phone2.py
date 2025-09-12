import pytest
import time
from seleniumwire import webdriver
from selenium.webdriver.common.by import By

@pytest.fixture
def driver():
    """Фикстура для запуска и закрытия браузера"""
    options = {'disable_encoding': True}
    driver = webdriver.Chrome(seleniumwire_options=options)
    driver.maximize_window()
    yield driver
    driver.quit()


def test_bottom_phone_consultation_request(driver):
    driver.get("https://aipradavan.city-innovation.kz/")
    time.sleep(2)  # Ждем полной загрузки страницы

    # Скроллим к нижней форме
    bottom_form = driver.find_elements(By.CSS_SELECTOR, "input[type='tel']")[-1]
    driver.execute_script("arguments[0].scrollIntoView(true);", bottom_form)
    time.sleep(1)

    # Вводим номер телефона во вторую форму
    bottom_form.clear()
    bottom_form.send_keys("+7 (777) 777-77-77")

    # Находим вторую кнопку "Получить консультацию" (в конце страницы)
    submit_btn = driver.find_elements(By.XPATH, "//button[contains(text(), 'Получить консультацию')]")[-1]
    submit_btn.click()

    # Ждем отправки запроса
    time.sleep(3)

    # Проверяем, что среди POST-запросов есть с кодом 200
    found_200 = False
    for request in driver.requests:
        if request.response and request.method == "POST":
            if request.response.status_code == 200:
                print(f"[OK] Запрос {request.url} вернул 200")
                found_200 = True
                break

    assert found_200, "Нет POST-запроса с кодом 200 для нижней формы"
