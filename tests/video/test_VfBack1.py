from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def test_video_playback():
    driver = webdriver.Chrome()
    driver.maximize_window()
    wait = WebDriverWait(driver, 20)

    try:
        # 1. Открываем сайт
        driver.get("https://test-frontik.city-innovation.kz/")

        # 2. Кликаем на кнопку "Отзывы"
        reviews_link = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//a[@href='/#testimonials']"))
        )
        reviews_link.click()
        time.sleep(2)

        # 3. Кликаем "Следующий отзыв"
        next_button = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[.//span[text()='Следующий отзыв']]")
        ))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
        driver.execute_script("arguments[0].click();", next_button)
        time.sleep(2)

        # 4. Кликаем Play у видео
        play_button = wait.until(EC.element_to_be_clickable((
            By.XPATH, "//div[@class='absolute inset-0 bg-black bg-opacity-30 flex items-center justify-center']//button"
        )))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", play_button)
        driver.execute_script("arguments[0].click();", play_button)

        # 5. Переходим в iframe YouTube
        iframe = wait.until(
            EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, 'youtube.com')]"))
        )
        driver.switch_to.frame(iframe)

        # 6. Ждём пока кнопка Play изменится на Pause (любой язык интерфейса)
        wait.until(lambda d: "ause" in d.find_element(
            By.CSS_SELECTOR, "button.ytp-play-button"
        ).get_attribute("aria-label"))

        print("✅ Видео успешно воспроизводится")

    finally:
        time.sleep(3)
        driver.quit()
