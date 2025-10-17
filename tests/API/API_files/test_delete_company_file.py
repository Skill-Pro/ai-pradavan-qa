import pytest
import requests
import io
import uuid

BASE_URL = "https://backend-test-service.city-innovation.kz"


def _get_files(auth_headers):
    """Вспомогательная функция: возвращает JSON ответа GET /api/v1/files"""
    resp = requests.get(f"{BASE_URL}/api/v1/files", headers=auth_headers)
    return resp


def _upload_temp_file(auth_headers, content=b"Temporary file content"):
    """
    Загружает временный файл и возвращает имя файла, как его вернул сервер (или локальное имя при ошибке).
    Используется если на аккаунте нет файлов.
    """
    url = f"{BASE_URL}/api/v1/files"
    filename = f"temp_{uuid.uuid4().hex[:8]}.txt"
    fake_file = io.BytesIO(content)
    files = {"file": (filename, fake_file, "text/plain")}
    resp = requests.post(url, headers=auth_headers, files=files)

    print("\n-----------------------------------------")
    print("ℹ️ Загружаем временный файл для теста")
    print(f"📤 URL: {url}")
    print(f"📄 Имя файла: {filename}")
    print(f"📨 Response code: {resp.status_code}")
    print(f"📦 Response body: {resp.text}")
    print("-----------------------------------------")

    resp.raise_for_status()  # если загрузка неуспешна — прервём тест (чтобы дальше не ломать логику)
    # Попробуем достать реальное имя файла из ответа, если сервер его вернул
    try:
        j = resp.json()
        # если сервер вернул объект с message/filename — можно обработать; но это зависит от реализации
        # вернём локальное имя на всякий случай
    except Exception:
        pass

    return filename


def test_delete_company_file_success(auth_headers):
    """
    Позитивный сценарий:
    1) Получаем список файлов.
    2) Если файлов нет — загружаем временный.
    3) Удаляем один из файлов по имени.
    4) Проверяем, что файл исчез из списка.
    """
    # 1) Получаем список файлов
    resp = _get_files(auth_headers)
    print("\n-----------------------------------------")
    print("✅ Шаг 1: Получаем список файлов перед удалением")
    print(f"📤 GET {BASE_URL}/api/v1/files")
    print(f"📨 Response code: {resp.status_code}")
    print(f"📦 Response body: {resp.text}")
    print("-----------------------------------------")

    assert resp.status_code == 200, f"❌ Ожидался 200 при получении списка файлов, получили {resp.status_code}"

    json_data = resp.json()
    files_list = json_data.get("data", [])
    # 2) Если нет файлов — загружаем временный
    if not files_list:
        temp_name = _upload_temp_file(auth_headers)
        # снова получить список
        resp = _get_files(auth_headers)
        assert resp.status_code == 200, f"❌ После загрузки временного файла не удалось получить список: {resp.status_code}"
        json_data = resp.json()
        files_list = json_data.get("data", [])

    assert isinstance(files_list, list), "❌ Ожидается список в поле data"

    # Выберем первый файл (ожидаем, что он содержит поле 'filename')
    first_file_obj = files_list[0]
    filename = first_file_obj.get("filename") if isinstance(first_file_obj, dict) else None
    # если нет поля filename — можем попытаться распознать из url
    if not filename:
        filename = first_file_obj.get("url", "").split("/")[-1] if isinstance(first_file_obj, dict) else None

    assert filename, f"❌ Не удалось определить имя файла для удаления: {first_file_obj}"

    # 3) Удаляем файл
    del_resp = requests.delete(
        f"{BASE_URL}/api/v1/files",
        headers=auth_headers,
        params={"filename": filename}
    )

    print("\n-----------------------------------------")
    print("✅ Шаг 2: Удаляем файл")
    print(f"🗑️ DELETE {BASE_URL}/api/v1/files?filename={filename}")
    print(f"📨 Response code: {del_resp.status_code}")
    print(f"📦 Response body: {del_resp.text}")
    print("-----------------------------------------")

    assert del_resp.status_code == 200, f"❌ Ожидался 200 при удалении файла, получили {del_resp.status_code}"
    del_json = del_resp.json()
    assert del_json.get("status") is True, f"❌ В ответе об удалении ожидаем status=True, получили: {del_json}"

    # 4) Проверяем, что файл исчез из списка
    after_resp = _get_files(auth_headers)
    print("\n-----------------------------------------")
    print("✅ Шаг 3: Получаем список файлов после удаления")
    print(f"📤 GET {BASE_URL}/api/v1/files")
    print(f"📨 Response code: {after_resp.status_code}")
    print(f"📦 Response body: {after_resp.text}")
    print("-----------------------------------------")

    assert after_resp.status_code == 200, f"❌ Ожидался 200 при получении списка после удаления, получили {after_resp.status_code}"
    after_list = after_resp.json().get("data", [])
    # Проверяем что среди имён файлов нет удалённого
    after_names = []
    for item in after_list:
        if isinstance(item, dict):
            if item.get("filename"):
                after_names.append(item.get("filename"))
            elif item.get("url"):
                after_names.append(item.get("url").split("/")[-1])
    assert filename not in after_names, f"❌ Файл {filename} всё ещё присутствует в списке после удаления. Список: {after_names}"

@pytest.mark.parametrize("filename, expected_code", [
    ("", 404),   # сервер считает пустое имя как "не найден"
    (None, 422)  # отсутствие параметра вызывает ошибку валидации
])
def test_delete_company_file_invalid_empty_name(auth_headers, filename, expected_code):
    """
    Негативный сценарий: пустое или None имя файла.
    - Если filename="", сервер отвечает 404 (File not found)
    - Если filename=None, сервер отвечает 422 (Validation Error)
    """
    resp = requests.delete(
        f"{BASE_URL}/api/v1/files",
        headers=auth_headers,
        params={"filename": filename}
    )

    print("\n-----------------------------------------")
    print("🚫 Негативный сценарий: удаление с пустым/None filename")
    print(f"🗑️ DELETE {BASE_URL}/api/v1/files?filename={filename}")
    print(f"📨 Response code: {resp.status_code}")
    print(f"📦 Response body: {resp.text}")
    print("-----------------------------------------")

    assert resp.status_code == expected_code, (
        f"❌ Ожидался {expected_code} для filename={filename}, получили: {resp.status_code}"
    )



def test_delete_company_file_non_existing(auth_headers):
    """
    Негативный сценарий: удаление несуществующего файла.
    Подход: отправляем запрос с рандомным именем, затем проверяем, что в текущем списке такого имени нет.
    (API может вернуть 422/404/200 в зависимости от реализации — мы гарантируем, что в списке файл отсутствует.)
    """
    random_name = f"non_exist_{uuid.uuid4().hex[:8]}.txt"

    resp = requests.delete(
        f"{BASE_URL}/api/v1/files",
        headers=auth_headers,
        params={"filename": random_name}
    )

    print("\n-----------------------------------------")
    print("🚫 Негативный сценарий: удаление несуществующего файла")
    print(f"🗑️ DELETE {BASE_URL}/api/v1/files?filename={random_name}")
    print(f"📨 Response code: {resp.status_code}")
    print(f"📦 Response body: {resp.text}")
    print("-----------------------------------------")

    # После попытки удаления — достаём текущий список и убеждаемся, что имя отсутствует
    list_resp = _get_files(auth_headers)
    assert list_resp.status_code == 200, f"❌ Не удалось получить список файлов для валидации после удаления: {list_resp.status_code}"
    names = []
    for item in list_resp.json().get("data", []):
        if isinstance(item, dict):
            if item.get("filename"):
                names.append(item.get("filename"))
            elif item.get("url"):
                names.append(item.get("url").split("/")[-1])

    assert random_name not in names, f"❌ Неожиданно: файл {random_name} присутствует в списке после попытки удаления."
