import requests

BASE_URL = "https://backend-test-service.city-innovation.kz"


def test_password_recovery_request():
    """🧪 Позитивный сценарий: запрос восстановления пароля по email"""

    url = f"{BASE_URL}/api/v1/auth/password/recovery"
    payload = {
        "email": "zangar.zhunisbekov@gmail.com"
    }

    response = requests.post(url, json=payload)

    print("\n-----------------------------------------")
    print("🧪 Позитивный сценарий: запрос восстановления пароля")
    print(f"📤 Payload: {payload}")
    print(f"📨 Response code: {response.status_code}")
    print(f"📦 Response body: {response.text}")
    print("-----------------------------------------")

    assert response.status_code == 200, "Ожидался код 200 при успешном запросе"
    data = response.json()
    assert data["status"] is True
    assert "message" in data


def test_password_recovery_invalid_email():
    """🚫 Негативный сценарий: невалидный или несуществующий email"""

    url = f"{BASE_URL}/api/v1/auth/password/recovery"
    payload = {
        "email": "not-an-email"
    }

    response = requests.post(url, json=payload)

    print("\n-----------------------------------------")
    print("🚫 Негативный сценарий: невалидный/несуществующий email")
    print(f"📤 Payload: {payload}")
    print(f"📨 Response code: {response.status_code}")
    print(f"📦 Response body: {response.text}")
    print("-----------------------------------------")

    # API возвращает 404, если пользователя нет
    assert response.status_code == 404, "Ожидался код 404 при отсутствии пользователя"
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


def test_password_recovery_empty_email():
    """🚫 Негативный сценарий: пустое поле email"""

    url = f"{BASE_URL}/api/v1/auth/password/recovery"
    payload = {
        "email": ""
    }

    response = requests.post(url, json=payload)

    print("\n-----------------------------------------")
    print("🚫 Негативный сценарий: пустое поле email")
    print(f"📤 Payload: {payload}")
    print(f"📨 Response code: {response.status_code}")
    print(f"📦 Response body: {response.text}")
    print("-----------------------------------------")

    # Если есть валидация — ожидаем 422, если нет — 404
    assert response.status_code in [404, 422], (
        f"Ожидался код 422 (валидация) или 404 (пользователь не найден), получен {response.status_code}"
    )
