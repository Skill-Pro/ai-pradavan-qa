import pytest
from playwright.sync_api import sync_playwright, expect

URL = "https://aipradavan.city-innovation.kz/"

@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        yield browser
        browser.close()

def fill_form(page, name, phone, email):
    page.fill("input[placeholder='Ваше имя']", name)
    page.fill("input[placeholder='Телефон']", phone)
    page.fill("input[placeholder='Email']", email)

def submit_and_check_status(page):
    """Отправка формы и проверка POST-запроса"""
    try:
        button = page.locator("form button:has-text('Стать партнёром')").first
        with page.expect_response(lambda r: r.request.method == "POST" and "partner" in r.url, timeout=5000) as response_info:
            button.click(force=True)
            page.wait_for_timeout(1000)  # даём немного времени запросу
        response = response_info.value
        print(f"[INFO] {response.url} → {response.status}")
        assert response.status == 200, f"Ожидался статус 200, пришёл {response.status}"
        return True
    except Exception as e:
        print(f"[ERROR] Не удалось поймать ответ: {e}")
        return False

def test_partner_form_valid(browser):
    """Тест с корректными данными"""
    page = browser.new_page()
    page.goto(URL)

    fill_form(page, "Иван Иванов", "+7 (777) 777-77-77", "test@example.com")
    assert submit_and_check_status(page), "Нет запроса с кодом 200"

    # Проверка UI успешной отправки
    success_locator = page.locator(".success-message")  # <-- укажи правильный селектор
    expect(success_locator).to_be_visible(timeout=5000)

    page.close()

@pytest.mark.parametrize("email", [
    "",  # пустое поле
    "testexample.com",  # нет @
    "test@",  # нет домена
    "t@c",  # слишком короткий
    "test@domain",  # нет точки в домене
])
def test_partner_form_invalid_email(browser, email):
    """Тест на некорректные email"""
    page = browser.new_page()
    page.goto(URL)

    fill_form(page, "Иван Иванов", "+7 (777) 777-77-77", email)
    button = page.locator("form button:has-text('Стать партнёром')").first
    button.click(force=True)

    page.wait_for_timeout(1000)  # небольшая задержка для UI

    # Проверка, что POST-запрос не отправился
    with pytest.raises(Exception):
        with page.expect_response(lambda r: r.request.method == "POST" and "partner" in r.url, timeout=3000):
            pass

    # Проверка UI сообщения об ошибке email
    error_locator = page.locator(".error-email")  # <-- укажи правильный селектор для ошибки
    expect(error_locator).to_be_visible(timeout=3000)

    page.close()
