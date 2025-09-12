import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

@pytest.fixture
def driver():
    driver = webdriver.Chrome()
    driver.maximize_window()
    yield driver
    driver.quit()

def capture_error(driver, error_msg):
    if not os.path.exists("screenshots"):
        os.mkdir("screenshots")
    screenshot_path = f"screenshots/error_{int(time.time())}.png"
    driver.save_screenshot(screenshot_path)
    pytest.fail(f"❌ {error_msg}. Скриншот: {screenshot_path}")

def test_profile_edit(driver):
    try:
        driver.get("https://test-frontik.city-innovation.kz/")

        # Вход
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//a[text()='Войти']"))).click()
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "email"))).send_keys("zangar.zhunisbekov@gmail.com")
        driver.find_element(By.ID, "password").send_keys("zangar1224")
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and text()='Войти']"))).click()

        WebDriverWait(driver, 10).until(EC.url_contains("dashboard"))

        # ⏳ Ждём немного — иногда Radix генерирует табы с задержкой
        time.sleep(3)

        # Найти кнопку "Аккаунт" и кликнуть
        # Скроллим по чуть-чуть вниз, пока не найдем кнопку
        for _ in range(5):
            try:
                account_button = driver.find_element(By.XPATH, "//button[text()='Аккаунт']")
                if account_button.is_displayed():
                    break
            except:
                pass
            driver.execute_script("window.scrollBy(0, 300);")
            time.sleep(0.5)

        # Далее — скролл к кнопке и клик
        driver.execute_script("arguments[0].scrollIntoView(true);", account_button)
        time.sleep(1)
        account_button.click()

        # Клик на кнопку "Редактировать"
        edit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Редактировать')]"))
        )
        edit_button.click()

        # Ввод данных
        company_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "company_name")))
        company_input.clear()
        company_input.send_keys("Компания")

        # Нажать сохранить
        save_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Сохранить')]"))
        )
        save_button.click()

    except Exception as e:
        capture_error(driver, f"Ошибка при редактировании профиля: {e}")
