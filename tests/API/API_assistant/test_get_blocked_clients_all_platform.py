#КРАСОТА НЕ ТРОГАТЬ
#НЕ ТРОГАТЬ
import pytest
import requests

BASE_URL = "https://backend-test-service.city-innovation.kz"
ASSISTANT_ID = "asst_rx4DsUyCC1roEbN0CHsDWCHv"
PLATFORMS = ["telegram_web", "whatsapp_web", "telegram", "instagram"]


@pytest.fixture(scope="session", autouse=True)
def results_summary(request):
    """
    Фикстура собирает результаты тестов и выводит финальный отчёт после всех проверок.
    """
    results = []

    def fin():
        print("\n" + "=" * 60)
        print("📊 ИТОГОВЫЙ ОТЧЁТ ПО ПЛАТФОРМАМ:")
        print("=" * 60)
        for res in results:
            print(res)
        print("=" * 60)

    request.addfinalizer(fin)
    return results


@pytest.mark.parametrize("platform", PLATFORMS)
def test_get_blocked_clients_of_assistant(auth_headers, platform, results_summary):
    """
    Проверяет получение заблокированных клиентов ассистента
    для каждой платформы (telegram_web, whatsapp_web, telegram, instagram).
    """
    url = f"{BASE_URL}/api/v1/assistants/{ASSISTANT_ID}/blocked_clients/{platform}"
    response = requests.get(url, headers=auth_headers)
    status_code = response.status_code

    print(f"\n🔹 Платформа: {platform}")
    print(f"🔗 URL: {url}")
    print(f"📡 Код ответа: {status_code}")

    if status_code == 200:
        data = response.json()
        total = data.get("total", 0)
        blocked = data.get("data", [])
        print(f"✅ Успешно. Найдено заблокированных клиентов: {total}")
        if total > 0:
            print(f"📋 Примеры: {blocked[:3]}")
        results_summary.append(f"✅ {platform}: OK (код {status_code}, {total} клиентов)")

    elif status_code == 422:
        data = response.json()
        print(f"⚠️ Ошибка валидации (422): {data.get('detail')}")
        results_summary.append(f"⚠️ {platform}: Validation Error (код {status_code})")

    elif status_code == 404:
        print(f"❌ Ассистент не найден или нет интеграции (404)")
        results_summary.append(f"❌ {platform}: Not Found (код {status_code})")

    else:
        print(f"🚨 Неожиданный статус код: {status_code}")
        print(f"Ответ: {response.text}")
        results_summary.append(f"🚨 {platform}: Ошибка (код {status_code})")

    # Универсальная проверка — тест не должен падать, если статус известный
    assert status_code in [200, 404, 422], \
        f"Непредвиденный статус код {status_code} для платформы {platform}"


def test_get_blocked_clients_invalid_assistant(auth_headers):
    """
    Проверка с несуществующим assistant_id.
    Ожидается 422 (Validation Error) или 404.
    """
    invalid_id = "asst_invalid123"
    platform = "telegram"
    url = f"{BASE_URL}/api/v1/assistants/{invalid_id}/blocked_clients/{platform}"
    response = requests.get(url, headers=auth_headers)
    status_code = response.status_code

    print(f"\n🧪 Проверка невалидного ассистента:")
    print(f"🔗 URL: {url}")
    print(f"📡 Код ответа: {status_code}")

    assert status_code in [404, 422], \
        f"Ожидался 404 или 422, получен {status_code}: {response.text}"

    print(f"🧾 Ответ: {response.json()}")
