import pytest
import requests
import json

BASE_URL = "https://backend-test-service.city-innovation.kz"


@pytest.mark.api
def test_get_assistants_positive(auth_headers, request):
    """
    🧪 Позитивный сценарий: получение списка помощников текущей компании.
    Проверяется:
    - статус код 200
    - корректная структура JSON
    - наличие обязательных полей у ассистентов
    """
    response = requests.get(f"{BASE_URL}/api/v1/assistants", headers=auth_headers)
    request.node.response_info = response.text  # лог в HTML-отчёт

    assert response.status_code == 200, f"❌ Ожидался статус 200, получено: {response.status_code}"
    json_data = response.json()

    assert "data" in json_data, "❌ В ответе отсутствует ключ 'data'"
    assert "total" in json_data, "❌ В ответе отсутствует ключ 'total'"
    assert isinstance(json_data["data"], list), "❌ Поле 'data' должно быть списком"

    if json_data["data"]:
        assistant = json_data["data"][0]
        required_fields = [
            "id", "name", "sphere", "language",
            "behavior", "company_information", "company_id",
            "created_at", "updated_at"
        ]
        missing_fields = [f for f in required_fields if f not in assistant]
        assert not missing_fields, f"❌ Отсутствуют поля: {missing_fields}"

    pretty_json = json.dumps(json_data, indent=2, ensure_ascii=False)
    print("\n✅ Успешный ответ API (GET /api/v1/assistants):\n")
    print(pretty_json)
    print("\n🟩 Тест успешно пройден.")


@pytest.mark.api
def test_get_assistants_unauthorized(request):
    """
    🚫 Негативный сценарий: запрос без токена авторизации.
    Ожидается статус-код 401.
    """
    headers = {"accept": "application/json"}
    response = requests.get(f"{BASE_URL}/api/v1/assistants", headers=headers)
    request.node.response_info = response.text

    assert response.status_code == 401, (
        f"❌ Ожидался статус 401 при отсутствии токена, получено: {response.status_code}"
    )

    print("\n🚫 Запрос без токена отклонён, как ожидалось.")
    print(f"Ответ: {response.text}")


@pytest.mark.api
def test_get_assistants_invalid_token(request):
    """
    🚫 Негативный сценарий: запрос с недействительным токеном.
    Ожидается статус-код 401 или 403.
    """
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer invalid_token_123"
    }

    response = requests.get(f"{BASE_URL}/api/v1/assistants", headers=headers)
    request.node.response_info = response.text

    assert response.status_code in [401, 403], (
        f"❌ Ожидался статус 401 или 403 при неверном токене, получено: {response.status_code}"
    )

    print("\n🚫 Запрос с неверным токеном отклонён, как ожидалось.")
    print(f"Ответ: {response.text}")
