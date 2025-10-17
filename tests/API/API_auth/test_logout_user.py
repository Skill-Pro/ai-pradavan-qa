import requests

BASE_URL = "https://backend-test-service.city-innovation.kz"
LOGIN_URL = f"{BASE_URL}/api/v1/auth/login"
LOGOUT_URL = f"{BASE_URL}/api/v1/auth/logout"

ADMIN_EMAIL = "nkAdmin@gmail.com"
ADMIN_PASSWORD = "12605291"


def test_logout_user_positive():
    """
    🧪 Позитивный сценарий: успешный выход из системы с refresh_token
    """
    # 🔹 1. Авторизация
    login_data = {
        "username": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
        "grant_type": "password"
    }

    login_response = requests.post(LOGIN_URL, data=login_data)
    assert login_response.status_code == 200, f"Ошибка логина: {login_response.text}"

    login_json = login_response.json()
    refresh_token = login_json.get("refresh_token")
    assert refresh_token, "Не удалось получить refresh_token"

    print(f"✅ Авторизация успешна. Refresh token: {refresh_token[:20]}...")

    # 🔹 2. Logout с refresh_token
    headers = {"Authorization": f"Bearer {refresh_token}"}
    logout_response = requests.post(LOGOUT_URL, headers=headers)

    # 🔹 3. Проверка успешного ответа
    assert logout_response.status_code == 200, f"Ошибка logout: {logout_response.text}"

    response_json = logout_response.json()
    assert response_json.get("status") is True, "Поле 'status' не True"
    assert "message" in response_json, "Поле 'message' отсутствует"

    print("🧪 Позитивный сценарий: успешный выход из системы")
    print(f"📨 Response code: {logout_response.status_code}")
    print(f"📦 Response body: {response_json}")


def test_logout_user_invalid_token():
    """
    🚫 Негативный сценарий: logout с некорректным токеном
    """
    invalid_token = "Bearer invalid_token_123"
    headers = {"Authorization": invalid_token}

    logout_response = requests.post(LOGOUT_URL, headers=headers)

    # Ожидаем 403 Forbidden
    assert logout_response.status_code == 403, "Должен вернуться статус 403 при неверном токене"

    response_json = logout_response.json()
    assert response_json.get("detail") == "Invalid token", f"Ожидалось 'Invalid token', получено: {response_json}"

    print("🚫 Негативный сценарий: неверный токен")
    print(f"📨 Response code: {logout_response.status_code}")
    print(f"📦 Response body: {response_json}")
