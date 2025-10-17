import pytest
import requests
import json

BASE_URL = "https://backend-test-service.city-innovation.kz/api/v1/assistants"


@pytest.mark.api
@pytest.mark.assistant
def test_update_assistant_positive(auth_headers, request):
    """
    ✅ Positive test: successfully update an assistant.
    """

    # Получаем список ассистентов, чтобы взять реальный id
    assistants_response = requests.get(BASE_URL, headers=auth_headers)
    assert assistants_response.status_code == 200, f"Ошибка при получении ассистентов: {assistants_response.text}"
    assistants_data = assistants_response.json()

    assistants = (
        assistants_data.get("assistants")
        or assistants_data.get("data")
        or assistants_data
        or []
    )
    assert assistants, "❌ Не найден ни один ассистент в текущей компании"
    assistant_id = assistants[0]["id"]

    body = {
        "name": "Updated Assistant",
        "additional_instructions": "Updated instructions",
        "sphere": "marketing",
        "language": "English",
        "behavior": "Friendly and concise",
        "company_information": "Updated company info",
        "id": assistant_id,
        "work_start": "09:00:00.000Z",
        "work_end": "18:00:00.000Z",
        "debounce_timer": 2
    }

    response = requests.put(BASE_URL, headers=auth_headers, json=body)

    # Сохраняем тело ответа в HTML отчёт
    request.node.response_info = f"Request body:\n{json.dumps(body, indent=2)}\n\nResponse:\n{response.text}"

    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    response_json = response.json()
    assert response_json.get("status") is True
    assert response_json.get("message") == "Assistant updated successfully"


@pytest.mark.api
@pytest.mark.assistant
def test_update_assistant_invalid_token(request):
    """
    ❌ Negative test: update with invalid token.
    """
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer invalid_token",
        "Content-Type": "application/json"
    }

    body = {
        "name": "Invalid Update",
        "additional_instructions": "string",
        "sphere": "string",
        "language": "string",
        "behavior": "string",
        "company_information": "string",
        "id": "asst_rx4DsUyCC1roEbN0CHsDWCHv",
        "work_start": "20:55:53.906Z",
        "work_end": "20:55:53.906Z",
        "debounce_timer": 0
    }

    response = requests.put(BASE_URL, headers=headers, json=body)

    request.node.response_info = f"Request body:\n{json.dumps(body, indent=2)}\n\nResponse:\n{response.text}"

    assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    response_text = response.text.lower()
    assert ("message" in response_text) or ("detail" in response_text), f"Expected 'message' or 'detail' key, got: {response_text}"


@pytest.mark.api
@pytest.mark.assistant
def test_update_assistant_missing_fields(auth_headers, request):
    """
    ❌ Negative test: missing required fields.
    """

    # Берём id ассистента для теста
    get_response = requests.get(BASE_URL, headers=auth_headers)
    assert get_response.status_code == 200, "Не удалось получить список ассистентов"
    assistants_data = get_response.json()

    assistants = (
        assistants_data.get("assistants")
        or assistants_data.get("data")
        or assistants_data
        or []
    )
    assert assistants, f"Нет ассистентов в ответе: {assistants_data}"
    assistant_id = assistants[0]["id"]

    body = {"id": assistant_id}  # намеренно неполное тело

    response = requests.put(BASE_URL, headers=auth_headers, json=body)

    request.node.response_info = f"Request body:\n{json.dumps(body, indent=2)}\n\nResponse:\n{response.text}"

    assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
    assert "message" in response.text or "error" in response.text or "detail" in response.text
