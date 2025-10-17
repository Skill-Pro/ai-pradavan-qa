import pytest
import requests
from datetime import datetime

BASE_URL = "https://backend-test-service.city-innovation.kz/api/v1"
ASSISTANT_ID = "asst_szVq6sls4ROJs5jHWXUlKWmp"


@pytest.mark.api
def test_update_dozhim_settings(auth_headers):
    """
    Проверяет успешное обновление настроек дожима ассистента.
    """

    url = f"{BASE_URL}/assistants/{ASSISTANT_ID}/dozhim/"
    print(f"\n➡️ PUT {url}")

    # Формируем данные для обновления
    payload = {
        "status": True,
        "timer": [5, 10, 15],
        "retry": 3,
        "promt": "Тестовое обновление настроек дожима",
        "work_start": datetime.utcnow().strftime("%H:%M:%S.%fZ"),
        "work_end": datetime.utcnow().strftime("%H:%M:%S.%fZ")
    }

    response = requests.put(url, headers=auth_headers, json=payload)

    # Проверяем, что запрос успешен
    assert response.status_code == 200, f"❌ Ожидался статус 200, получен {response.status_code}: {response.text}"

    try:
        data = response.json()
    except Exception:
        pytest.fail(f"❌ Ответ не в формате JSON:\n{response.text}")

    # Проверка ключей и типов данных
    expected_keys = {"status", "timer", "retry", "promt", "work_start", "work_end"}
    assert expected_keys.issubset(data.keys()), f"❌ Отсутствуют поля: {data.keys()}"

    assert isinstance(data["status"], bool), "Поле 'status' должно быть типа bool"
    assert isinstance(data["timer"], list), "Поле 'timer' должно быть массивом"
    assert isinstance(data["retry"], int), "Поле 'retry' должно быть числом"
    assert isinstance(data["promt"], str), "Поле 'promt' должно быть строкой"
    assert isinstance(data["work_start"], str), "Поле 'work_start' должно быть строкой"
    assert isinstance(data["work_end"], str), "Поле 'work_end' должно быть строкой"

    # Проверяем, что ответ совпадает с отправленными данными (где возможно)
    assert data["status"] == payload["status"]
    assert data["retry"] == payload["retry"]
    assert data["promt"] == payload["promt"]

    print(f"✅ Настройки дожима успешно обновлены:\n{data}")


@pytest.mark.api
def test_update_dozhim_settings_invalid_id(auth_headers):
    """
    Проверяет, что при неверном ID ассистента возвращается ошибка 422 или 404.
    """

    invalid_id = "invalid_assistant_id"
    url = f"{BASE_URL}/assistants/{invalid_id}/dozhim/"
    payload = {
        "status": True,
        "timer": [1],
        "retry": 1,
        "promt": "Тест неверного ID",
        "work_start": datetime.utcnow().strftime("%H:%M:%S.%fZ"),
        "work_end": datetime.utcnow().strftime("%H:%M:%S.%fZ")
    }

    print(f"\n➡️ PUT {url}")

    response = requests.put(url, headers=auth_headers, json=payload)

    assert response.status_code in [404, 422], (
        f"❌ Ожидался статус 422 или 404, получен {response.status_code}: {response.text}"
    )

    print(f"⚠️ Ответ при неверном ID: {response.status_code}, {response.text}")
