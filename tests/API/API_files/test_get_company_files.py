import pytest
import requests

BASE_URL = "https://backend-test-service.city-innovation.kz"


def test_get_company_files_success(auth_headers):
    """
    Проверяет успешное получение списка файлов компании.
    """
    url = f"{BASE_URL}/api/v1/files"

    response = requests.get(url, headers=auth_headers)

    print("\n-----------------------------------------")
    print("✅ Позитивный сценарий: получение списка файлов компании")
    print(f"📤 URL: {url}")
    print(f"📨 Response code: {response.status_code}")
    print(f"📦 Response body: {response.text}")
    print("-----------------------------------------")

    # Проверка статус-кода
    assert response.status_code == 200, f"❌ Код ответа: {response.status_code}, ответ: {response.text}"

    json_data = response.json()

    # Проверка структуры ответа
    assert "data" in json_data, "❌ В ответе отсутствует поле 'data'"
    assert "total" in json_data, "❌ В ответе отсутствует поле 'total'"
    assert isinstance(json_data["data"], list), f"❌ Поле 'data' должно быть списком, получили: {type(json_data['data'])}"

    # Если файлы есть — проверим структуру первого
    if json_data["data"]:
        first_file = json_data["data"][0]
        assert "filename" in first_file, "❌ В объекте файла отсутствует поле 'filename'"
        assert "url" in first_file, "❌ В объекте файла отсутствует поле 'url'"


def test_get_company_files_unauthorized():
    """
    Проверяет, что без токена доступ к списку файлов запрещен.
    """
    url = f"{BASE_URL}/api/v1/files"

    response = requests.get(url)

    print("\n-----------------------------------------")
    print("🚫 Негативный сценарий: запрос без токена авторизации")
    print(f"📤 URL: {url}")
    print(f"📨 Response code: {response.status_code}")
    print(f"📦 Response body: {response.text}")
    print("-----------------------------------------")

    assert response.status_code in [401, 403], (
        f"❌ Ожидался 401 или 403, получили: {response.status_code}"
    )
