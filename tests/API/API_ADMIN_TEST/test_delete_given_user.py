import pytest
import requests
import json

BASE_URL = "https://backend-test-service.city-innovation.kz"
ADMIN_EMAIL = "nkAdmin@gmail.com"
ADMIN_PASSWORD = "12605291"


@pytest.fixture(scope="session")
def admin_token():
    """Авторизация админа и получение access_token"""
    url = f"{BASE_URL}/api/v1/auth/login"
    payload = {
        "username": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
        "grant_type": "password"
    }

    response = requests.post(url, data=payload)
    assert response.status_code == 200, f"Ошибка авторизации: {response.text}"

    token = response.json().get("access_token")
    assert token, "Токен не найден в ответе!"
    return token


@pytest.fixture
def auth_headers(admin_token):
    """Заголовки с токеном"""
    return {"Authorization": f"Bearer {admin_token}"}


def get_all_users(headers):
    """Получаем всех пользователей (постранично)"""
    all_users = []
    skip = 0
    limit = 100

    while True:
        url = f"{BASE_URL}/api/v1/admin/platform_users?skip={skip}&limit={limit}"
        resp = requests.get(url, headers=headers)
        assert resp.status_code == 200, f"Ошибка при запросе пользователей: {resp.text}"

        data = resp.json()
        users = data.get("data", [])
        if not users:
            break

        all_users.extend(users)
        skip += limit

        if len(users) < limit:
            break  # достигнут конец списка

    return all_users


def test_delete_test_users(auth_headers):
    """Удаление всех пользователей, у которых email начинается на 'test_'"""
    users_data = get_all_users(auth_headers)
    test_users = [u for u in users_data if u["email"].startswith("test_")]

    if not test_users:
        pytest.skip("Нет пользователей с email, начинающимся на 'test_'")

    deleted = []

    for user in test_users:
        user_id = user["id"]
        email = user["email"]
        del_url = f"{BASE_URL}/api/v1/admin/platform_users/{user_id}"

        del_response = requests.delete(del_url, headers=auth_headers)
        status_code = del_response.status_code
        resp_json = del_response.json() if del_response.text else {}

        print(f"\nУдаляю {email} → [{status_code}] {json.dumps(resp_json, ensure_ascii=False)}")

        assert status_code == 200, f"Ошибка при удалении {email}: {del_response.text}"
        assert resp_json.get("status") is True, f"Удаление {email} не подтвердилось: {resp_json}"

        deleted.append(email)

    print(f"\n✅ Успешно удалены пользователи: {deleted}")
