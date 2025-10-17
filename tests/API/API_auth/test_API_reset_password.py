#это работает но не работает так как токен каждый раз меняется и его нельзя автоматизовать для теста
#это работает но не работает так как токен каждый раз меняется и его нельзя автоматизовать для теста
#это работает но не работает так как токен каждый раз меняется и его нельзя автоматизовать для теста
#это работает но не работает так как токен каждый раз меняется и его нельзя автоматизовать для теста
# можно в ручную токен каждый раз менять
# можно в ручную токен каждый раз менять
# можно в ручную токен каждый раз менять
# можно в ручную токен каждый раз менять

import requests

BASE_URL = "https://backend-test-service.city-innovation.kz/api/v1/auth"
RECOVERY_URL = f"{BASE_URL}/password/recovery"
RESET_URL = f"{BASE_URL}/password/reset"
LOGIN_URL = f"{BASE_URL}/login"


def test_full_password_reset_flow():
    """
    🔄 Сквозной сценарий: восстановление пароля и авторизация с новым паролем
    """
    # 1️⃣ Шаг: запрос восстановления пароля
    recovery_payload = {"email": "zangar.zhunisbekov@gmail.com"}
    recovery_response = requests.post(RECOVERY_URL, json=recovery_payload)

    print("\n-----------------------------------------")
    print("🧪 Шаг 1: Запрос восстановления пароля")
    print("📦 Payload:", recovery_payload)
    print("📨 Response code:", recovery_response.status_code)
    print("📨 Response body:", recovery_response.text)
    print("-----------------------------------------")

    assert recovery_response.status_code == 200
    assert recovery_response.json()["status"] is True

    # 2️⃣ Шаг: сброс пароля (используем токен восстановления)
    reset_payload = {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ6YW5nYXIuemh1bmlzYmVrb3ZAZ21haWwuY29tIiwiaWQiOjE3MSwidHlwZSI6InJlY292ZXJ5IiwianRpIjoiMmJlZmJhYTctMzliMS00ZGJhLWI5ZWItNWI2NzAwYjQzZmI2IiwiaWF0IjoxNzYwMDA5ODU0LCJleHAiOjE3NjAwMTE2NTR9._ghZIxJ-WqMV4_WDWJSpkgOjOmuhS9d2-5pZetuMYhI",
        "password": "NewPassword123!"
    }
    reset_response = requests.post(RESET_URL, json=reset_payload)

    print("\n-----------------------------------------")
    print("🧪 Шаг 2: Сброс пароля")
    print("📦 Payload:", reset_payload)
    print("📨 Response code:", reset_response.status_code)
    print("📨 Response body:", reset_response.text)
    print("-----------------------------------------")

    assert reset_response.status_code == 200
    reset_data = reset_response.json()
    assert "access_token" in reset_data
    assert "refresh_token" in reset_data
    assert reset_data["token_type"] == "Bearer"

    # 3️⃣ Шаг: авторизация с новым паролем (x-www-form-urlencoded)
    login_payload = {
        "grant_type": "password",
        "username": "zangar.zhunisbekov@gmail.com",
        "password": "NewPassword123!",
        "scope": "",
        "client_id": "",
        "client_secret": ""
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    login_response = requests.post(LOGIN_URL, data=login_payload, headers=headers)

    print("\n-----------------------------------------")
    print("🧪 Шаг 3: Авторизация с новым паролем")
    print("📦 Payload:", login_payload)
    print("📨 Response code:", login_response.status_code)
    print("📨 Response body:", login_response.text)
    print("-----------------------------------------")

    assert login_response.status_code == 200, f"Ошибка входа: {login_response.text}"
    login_data = login_response.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data
    assert login_data["token_type"] == "Bearer"

    print("✅ Сквозной сценарий успешно пройден!")
