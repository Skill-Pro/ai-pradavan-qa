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
        "email": "TEStest@gmail.com"
    }

    response = requests.post(url, json=payload)

    print("\n-----------------------------------------")
    print("🚫 Негативный сценарий: невалидный/несуществующий email")
    print(f"📤 Payload: {payload}")
    print(f"📨 Response code: {response.status_code}")
    print(f"📦 Response body: {response.text}")
    print("-----------------------------------------")

    # На текущей версии API ожидаем 404, если email не найден
    assert response.status_code == 404, "Ожидался код 404, если пользователь не найден"
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()
