import pytest
import requests
import io

BASE_URL = "https://backend-test-service.city-innovation.kz"


def test_upload_company_file_success(auth_headers):
    """
    Проверяет успешную загрузку файла компании.
    """
    url = f"{BASE_URL}/api/v1/files"

    fake_file = io.BytesIO(b"Test file content for company upload")
    files = {"file": ("test.txt", fake_file, "text/plain")}

    response = requests.post(url, headers=auth_headers, files=files)

    print("\n-----------------------------------------")
    print("✅ Позитивный сценарий: успешная загрузка файла компании")
    print(f"📤 URL: {url}")
    print(f"📄 Загруженный файл: {files['file'][0]}")
    print(f"📨 Response code: {response.status_code}")
    print(f"📦 Response body: {response.text}")
    print("-----------------------------------------")

    assert response.status_code == 200, f"❌ Код ответа: {response.status_code}, ответ: {response.text}"

    json_data = response.json()
    assert json_data.get("status") is True, f"❌ Ожидался status=True, но получили: {json_data}"
    assert "message" in json_data, "❌ В ответе отсутствует поле 'message'"


def test_upload_company_file_without_file(auth_headers):
    """
    Проверяет, что без файла возвращается ошибка 422.
    """
    url = f"{BASE_URL}/api/v1/files"

    response = requests.post(url, headers=auth_headers)

    print("\n-----------------------------------------")
    print("🚫 Негативный сценарий: попытка загрузить без файла")
    print(f"📤 URL: {url}")
    print(f"📨 Response code: {response.status_code}")
    print(f"📦 Response body: {response.text}")
    print("-----------------------------------------")

    assert response.status_code == 422, f"❌ Ожидался 422, получили: {response.status_code}"

    json_data = response.json()
    assert "detail" in json_data, "❌ В ответе отсутствует поле 'detail'"
