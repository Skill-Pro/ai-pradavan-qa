import pytest
import requests

BASE_URL = "https://backend-test-service.city-innovation.kz/api/v1/auth"
LOGIN_URL = f"{BASE_URL}/login"
REFRESH_URL = f"{BASE_URL}/token/refresh"

USERNAME = "nkAdmin@gmail.com"
PASSWORD = "12605291"


@pytest.fixture
def get_tokens():
    """Фикстура: логинится и возвращает access_token и refresh_token"""
    data = {
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
        "scope": "",
        "client_id": "",
        "client_secret": ""
    }

    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(LOGIN_URL, data=data, headers=headers)
    assert response.status_code == 200, f"❌ Ошибка логина: {response.text}"

    tokens = response.json()
    return tokens["access_token"], tokens["refresh_token"]


def test_refresh_token_success(get_tokens):
    """✅ Позитивный сценарий: обновление access_token"""
    old_access_token, refresh_token = get_tokens

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {refresh_token}"  # ✅ refresh используется как Bearer
    }

    response = requests.post(REFRESH_URL, json={"refresh_token": refresh_token}, headers=headers)

    print("Response:", response.text)
    assert response.status_code == 200, f"❌ Ошибка обновления: {response.text}"

    body = response.json()
    assert "access_token" in body, "❌ В ответе нет access_token"
    assert "refresh_token" in body, "❌ В ответе нет refresh_token"

    new_access_token = body["access_token"]
    assert new_access_token != old_access_token, "❌ Новый access_token совпадает со старым!"


def test_refresh_token_invalid():
    """🚫 Негативный сценарий: неверный refresh_token"""
    headers = {"accept": "application/json"}
    response = requests.post(REFRESH_URL, json={"refresh_token": "invalid_token"}, headers=headers)
    print("Response:", response.text)
    assert response.status_code in [400, 403, 422], f"❌ Ожидался 400/403/422, получен {response.status_code}"


def test_refresh_token_empty():
    """🚫 Негативный сценарий: пустой refresh_token"""
    headers = {"accept": "application/json"}
    response = requests.post(REFRESH_URL, json={"refresh_token": ""}, headers=headers)
    print("Response:", response.text)
    assert response.status_code in [400, 403, 422], f"❌ Ожидался 400/403/422, получен {response.status_code}"
