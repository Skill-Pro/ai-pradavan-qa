import requests
import pytest
import json

BASE_URL = "https://backend-test-service.city-innovation.kz/api/v1/auth"


def post_login(username, password):
    url = f"{BASE_URL}/login"
    return requests.post(url, data={"username": username, "password": password})


def format_response_info(response):
    """
    Форматируем ответ: статус-код + reason + тело ответа (JSON или текст).
    """
    status_line = f"{response.status_code} {response.reason}"
    try:
        body = response.json()
        pretty = json.dumps(body, ensure_ascii=False, indent=2)
        return f"{status_line}\n\n{pretty}"
    except ValueError:
        return f"{status_line}\n\n{response.text}"


# ====== позитивный тест ======
def test_login_success(request):
    r = post_login("testTEST@gmail.com", "test1234")
    request.node.response_info = format_response_info(r)
    assert r.status_code == 200, f"Expected 200 OK, got:\n{request.node.response_info}"


# ====== негативные тесты ======
def test_login_invalid_password(request):
    r = post_login("testTEST@gmail.com", "wrongpassword")
    request.node.response_info = format_response_info(r)
    assert r.status_code != 200, f"Invalid password passed:\n{request.node.response_info}"


def test_login_invalid_username(request):
    r = post_login("fake.email@example.com", "test1234")
    request.node.response_info = format_response_info(r)
    assert r.status_code != 200, f"Invalid username passed:\n{request.node.response_info}"


@pytest.mark.parametrize("username,password", [
    ("", "test1234"),
    ("testTEST@gmail.com", ""),
    ("", ""),
])
def test_login_empty_fields(request, username, password):
    r = post_login(username, password)
    request.node.response_info = format_response_info(r)
    assert r.status_code != 200, f"Empty fields passed:\n{request.node.response_info}"
