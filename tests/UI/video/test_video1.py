import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

def test_video_play_from_test_frontik():
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.maximize_window()

    try:
        # 1) Открываем сайт
        driver.get("https://test-frontik.city-innovation.kz/")

        # 2) Нажимаем на "Как это работает"
        how_it_works_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Как это работает"))
        )
        how_it_works_btn.click()

        # 3) Ждём появления iframe c видео и переключаемся в него
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
        )
        driver.switch_to.frame(iframe)

        # 4) Ждём кнопку "Play" и кликаем
        play_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".ytp-large-play-button"))
        )
        play_btn.click()

        # 5) Небольшая пауза для уверенности
        time.sleep(2)

        # 6) Проверяем, что кнопка Play сменилась на Pause
        WebDriverWait(driver, 10).until(
            lambda d: "ytp-paused" not in d.find_element(By.CSS_SELECTOR, ".ytp-play-button").get_attribute("class")
        )

        # 7) Проверяем, что видео реально проигрывается, проверяя прогресс
        current_time_1 = driver.execute_script("return document.querySelector('video').currentTime;")
        time.sleep(2)
        current_time_2 = driver.execute_script("return document.querySelector('video').currentTime;")

        assert current_time_2 > current_time_1, "Видео не воспроизводится — текущее время не увеличилось"

    finally:
        driver.quit()
