import pytest
import requests
import json

BASE_URL = "https://backend-test-service.city-innovation.kz"


@pytest.mark.parametrize("assistant_id", [
    "asst_rx4DsUyCC1roEbN0CHsDWCHv"  # ✅ замените на реальный ID ассистента из вашей компании
])
def test_check_assistant_blocked_positive(assistant_id, auth_headers):
    """
    ✅ Позитивный сценарий: Проверка, полностью ли заблокирован assistant.
    """
    url = f"{BASE_URL}/api/v1/assistants/{assistant_id}/blocked"
    headers = auth_headers

    response = requests.get(url, headers=headers)
    response_json = response.json()

    print("\n-----------------------------------------")
    print("🟢 Позитивный сценарий: Проверка блокировки ассистента")
    print(f"📤 URL: {url}")
    print(f"📨 Response code: {response.status_code}")
    print(f"📦 Response body: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
    print("-----------------------------------------")

    assert response.status_code == 200, f"Ожидался 200, получен {response.status_code}"
    assert "status" in response_json, "В ответе нет поля 'status'"
    assert isinstance(response_json["status"], bool), "Поле 'status' должно быть bool"
    assert "message" in response_json, "В ответе нет поля 'message'"


def test_check_assistant_blocked_invalid_id(auth_headers):
    """
    🚫 Негативный сценарий: Проверка при невалидном/несуществующем ID ассистента.
    Ожидается 404 (ассистент не найден).
    """
    invalid_id = "invalid-id"
    url = f"{BASE_URL}/api/v1/assistants/{invalid_id}/blocked"
    headers = auth_headers

    response = requests.get(url, headers=headers)
    response_json = response.json() if response.text else {}

    print("\n-----------------------------------------")
    print("🚫 Негативный сценарий: невалидный/несуществующий assistant_id")
    print(f"📤 URL: {url}")
    print(f"📨 Response code: {response.status_code}")
    print(f"📦 Response body: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
    print("-----------------------------------------")

    # ✅ исправлено ожидаемое значение с 422 → 404
    assert response.status_code == 404, f"Ожидался 404, получен {response.status_code}"
    assert "detail" in response_json or "message" in response_json, "В ответе нет деталей об ошибке"
