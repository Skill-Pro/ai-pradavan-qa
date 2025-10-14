import pytest
import requests
import json

BASE_URL = "https://backend-test-service.city-innovation.kz"


@pytest.mark.api
def test_create_new_assistant_success(new_user_headers, request):
    """
    ✅ Проверяет успешное создание нового помощника на чистом аккаунте.
    """
    url = f"{BASE_URL}/api/v1/assistants"
    payload = {
        "name": "Тестовый помощник",
        "additional_instructions": "Отвечай вежливо и кратко",
        "sphere": "Обслуживание клиентов",
        "language": "ru",
        "behavior": "дружелюбный",
        "company_information": "Компания TestCorp"
    }

    print("\n" + "=" * 80)
    print("🚀 ТЕСТ: Создание нового помощника (успешный сценарий)")
    print("=" * 80)
    print(f"📍 URL: {url}")
    print(f"📦 Тело запроса (payload):\n{json.dumps(payload, indent=4, ensure_ascii=False)}")

    # --- Выполняем запрос ---
    response = requests.post(url, json=payload, headers=new_user_headers)
    response_body = response.json()

    print("-" * 80)
    print(f"📨 Код ответа: {response.status_code}")
    print(f"📨 Тело ответа:\n{json.dumps(response_body, indent=4, ensure_ascii=False)}")
    print("-" * 80)

    # Добавляем ответ в HTML отчёт
    request.node.response_info = json.dumps(response_body, indent=4, ensure_ascii=False)

    # --- Проверки ---
    assert response.status_code == 200, f"❌ Ошибка при создании помощника: {response.text}"
    assert response_body.get("status") is True, f"❌ Некорректный статус: {response_body}"
    assert "message" in response_body, f"❌ Поле 'message' отсутствует в ответе: {response_body}"

    print("✅ Результат: Помощник успешно создан ✅")
    print("=" * 80)


@pytest.mark.api
def test_create_new_assistant_validation_error(new_user_headers, request):
    """
    ❌ Проверяет, что API корректно обрабатывает невалидные данные (например, без имени).
    """
    url = f"{BASE_URL}/api/v1/assistants"
    payload = {
        # отсутствует "name"
        "additional_instructions": "Без имени",
        "sphere": "Test",
        "language": "ru",
        "behavior": "формальный",
        "company_information": "Test Company"
    }

    print("\n" + "=" * 80)
    print("🚫 ТЕСТ: Создание помощника без имени (ошибка валидации)")
    print("=" * 80)
    print(f"📍 URL: {url}")
    print(f"📦 Тело запроса (payload):\n{json.dumps(payload, indent=4, ensure_ascii=False)}")

    # --- Выполняем запрос ---
    response = requests.post(url, json=payload, headers=new_user_headers)
    response_body = response.json()

    print("-" * 80)
    print(f"📨 Код ответа: {response.status_code}")
    print(f"📨 Тело ответа:\n{json.dumps(response_body, indent=4, ensure_ascii=False)}")
    print("-" * 80)

    # Добавляем ответ в HTML отчёт
    request.node.response_info = json.dumps(response_body, indent=4, ensure_ascii=False)

    # --- Проверки ---
    assert response.status_code == 422, f"❌ Ожидался код 422, но получен {response.status_code}"
    assert "detail" in response_body, f"❌ Поле 'detail' отсутствует в ответе: {response_body}"

    print("✅ Результат: Сервер корректно обработал невалидные данные ✅")
    print("=" * 80)
