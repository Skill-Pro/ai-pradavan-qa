import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


def test_video_playback_in_reviews():
    driver = webdriver.Chrome()
    driver.maximize_window()
    wait = WebDriverWait(driver, 20)

    try:
        # 1. Открываем сайт
        driver.get("https://test-frontik.city-innovation.kz/")

        # 2. Жмём кнопку "Отзывы"
        reviews_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='/#testimonials']"))
        )
        reviews_btn.click()

        # 3. Ждём появления блока с iframe и скроллим к нему
        reviews_iframe = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "section#testimonials iframe")
            )
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", reviews_iframe)

        # 4. Переключаемся в iframe
        driver.switch_to.frame(reviews_iframe)

        # 5. Жмём кнопку Play
        yt_play_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.ytp-large-play-button"))
        )
        driver.execute_script("arguments[0].click();", yt_play_button)

        # 6. Проверяем, что видео реально пошло (aria-label → Pause)
        wait.until(lambda d: "ause" in d.find_element(
            By.CSS_SELECTOR, "button.ytp-play-button"
        ).get_attribute("aria-label"))

        print("✅ Видео в блоке 'Отзывы' успешно воспроизводится")

    except TimeoutException as e:
        raise AssertionError("⛔ Видео в блоке 'Отзывы' не воспроизвелось: " + str(e))

    finally:
        time.sleep(3)
        driver.quit()
