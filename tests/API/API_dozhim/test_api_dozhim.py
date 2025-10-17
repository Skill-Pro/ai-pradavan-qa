import pytest
import requests

BASE_URL = "https://backend-test-service.city-innovation.kz/api/v1"
ASSISTANT_ID = "asst_szVq6sls4ROJs5jHWXUlKWmp"  # пример ID, замени на актуальный


@pytest.mark.api
def test_get_dozhim_settings(auth_headers):
    """
    Проверяет успешное получение дожим настроек ассистента.
    """

    url = f"{BASE_URL}/assistants/{ASSISTANT_ID}/dozhim/"
    print(f"\n➡️ GET {url}")

    response = requests.get(url, headers=auth_headers)

    # Проверяем код статуса
    assert response.status_code == 200, f"❌ Ожидался статус 200, получен {response.status_code}: {response.text}"

    try:
        data = response.json()
    except Exception:
        pytest.fail(f"❌ Ответ не в формате JSON:\n{response.text}")

    # Проверяем ключи
    expected_keys = {"status", "timer", "retry", "promt", "work_start", "work_end"}
    assert expected_keys.issubset(data.keys()), f"❌ Отсутствуют поля: {data.keys()}"

    # Проверка типов
    assert isinstance(data["status"], bool), "Поле 'status' должно быть типа bool"
    assert isinstance(data["timer"], list), "Поле 'timer' должно быть массивом"
    assert isinstance(data["retry"], int), "Поле 'retry' должно быть числом"
    assert isinstance(data["promt"], str), "Поле 'promt' должно быть строкой"
    assert isinstance(data["work_start"], str), "Поле 'work_start' должно быть строкой"
    assert isinstance(data["work_end"], str), "Поле 'work_end' должно быть строкой"

    print(f"✅ Настройки дожима получены успешно: {data}")


@pytest.mark.api
def test_get_dozhim_settings_invalid_id(auth_headers):
    """
    Проверяет, что при передаче неверного ID ассистента возвращается 422.
    """

    invalid_id = "invalid_id"
    url = f"{BASE_URL}/assistants/{invalid_id}/dozhim/"
    print(f"\n➡️ GET {url}")

    response = requests.get(url, headers=auth_headers)

    # Проверяем, что API возвращает ошибку (422)
    assert response.status_code in [404, 422], (
        f"❌ Ожидался статус 422 или 404 при неверном ID, получен {response.status_code}: {response.text}"
    )

    print(f"⚠️ Ответ при неверном ID: {response.status_code}, {response.text}")
