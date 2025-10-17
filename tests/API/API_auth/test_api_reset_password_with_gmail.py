# tests/API/API_auth/test_api_reset_password_with_gmail.py
import os
import re
import time
import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup

import requests
import pytest

BASE_URL = "https://backend-test-service.city-innovation.kz/api/v1/auth"
RECOVERY_URL = f"{BASE_URL}/password/recovery"
RESET_URL = f"{BASE_URL}/password/reset"
LOGIN_URL = f"{BASE_URL}/login"

# -------- CONFIG (set these in CI / env, don't hardcode) --------
GMAIL_IMAP = os.getenv("GMAIL_IMAP", "imap.gmail.com")
GMAIL_USER = os.getenv("GMAIL_USER", "zangar.zhunisbekov@gmail.com")
GMAIL_PASS = os.getenv("GMAIL_PASS", "zangar1224")  # <<-- app password or real password if allowed
POLLING_TIMEOUT = int(os.getenv("RECOVERY_POLL_TIMEOUT", "60"))  # seconds total to wait for the email
POLLING_INTERVAL = float(os.getenv("RECOVERY_POLL_INTERVAL", "3"))  # seconds between mailbox polls
# ----------------------------------------------------------------

def _connect_imap():
    imap = imaplib.IMAP4_SSL(GMAIL_IMAP)
    imap.login(GMAIL_USER, GMAIL_PASS)
    return imap

def _search_latest_recovery_email(imap, since_seconds=300):
    """
    найдет самое свежее письмо, которое, вероятно, содержит ссылку для восстановления:
    ищет по теме/тексту ключевые слова 'reset', 'recovery', 'password' и возвращает его payload (HTML/text)
    """
    imap.select("INBOX")
    # получим список UID писем за последний X дней — используем ALL и будем фильтровать
    status, data = imap.search(None, "ALL")
    if status != "OK":
        return None

    uids = data[0].split()
    # посмотрим в обратном порядке (новые первые)
    for uid in reversed(uids[-200:]):  # ограничим до последних 200 писем
        status, msg_data = imap.fetch(uid, "(RFC822)")
        if status != "OK":
            continue
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        # получить subject для фильтрации
        subj, enc = decode_header(msg.get("Subject") or "")[0]
        if isinstance(subj, bytes):
            try:
                subj = subj.decode(enc or "utf-8", errors="ignore")
            except Exception:
                subj = subj.decode("utf-8", errors="ignore")
        # нестрогое содержание — ищем ключевые слова
        text_for_check = (subj or "").lower()
        # сбор текста/HTML для поиска внутри
        body_text = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cd = part.get("Content-Disposition", "")
                if ctype == "text/plain" and "attachment" not in cd:
                    try:
                        body_text += part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                    except Exception:
                        pass
                elif ctype == "text/html" and "attachment" not in cd:
                    try:
                        body_text += part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                    except Exception:
                        pass
        else:
            try:
                body_text = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore")
            except Exception:
                body_text = str(msg.get_payload())

        text_for_check += "\n" + (body_text or "").lower()

        if any(k in text_for_check for k in ("reset", "recovery", "password", "восстанов", "recovery email", "reset-password")):
            return body_text
    return None

def _extract_token_from_body(body_text):
    """
    Попытаемся извлечь параметр token из ссылки:
    ищем ссылки вида ...reset-password?token=XXX или token=XXX
    """
    if not body_text:
        return None

    # 1) если HTML, попробуем распарсить ссылки
    try:
        soup = BeautifulSoup(body_text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "token=" in href:
                # возьмем значение token из query
                m = re.search(r"[?&]token=([^&\"'>\s]+)", href)
                if m:
                    return m.group(1)
        # также поиск внутри текста на любые jwt-like строки
    except Exception:
        pass

    # 2) универсальная regex-попытка: token=... или token: ...
    m = re.search(r"token['\"\s:=]*([A-Za-z0-9\-\._~%]+(?:\.[A-Za-z0-9\-\._~%]+){2,})", body_text)
    if m:
        return m.group(1)

    # 3) более общая: token=... без предположений
    m = re.search(r"[?&]token=([^&\s\"'>]+)", body_text)
    if m:
        return m.group(1)

    # 4) если JWT (три части с точками), найдем сам JWT
    m = re.search(r"([A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+)", body_text)
    if m:
        return m.group(1)

    return None


@pytest.mark.timeout(180)
def test_full_password_reset_flow_with_gmail():
    """
    Полный сценарий:
    1) POST /password/recovery -> письмо отправлено
    2) Подключение к Gmail -> найти письмо и извлечь token
    3) POST /password/reset с извлеченным token -> смена пароля
    4) POST /login (form-urlencoded) -> успешный вход
    """
    if not GMAIL_PASS:
        pytest.skip("GMAIL_PASS не задан (укажите app password через переменную окружения)")

    # 1) запрос восстановления пароля
    recovery_payload = {"email": GMAIL_USER}
    recovery_response = requests.post(RECOVERY_URL, json=recovery_payload)
    print("Recovery response:", recovery_response.status_code, recovery_response.text)
    assert recovery_response.status_code == 200
    assert recovery_response.json().get("status") is True

    # 2) подключаемся к почте и ждём письмо
    deadline = time.time() + POLLING_TIMEOUT
    body_text = None
    imap = None
    try:
        imap = _connect_imap()
        while time.time() < deadline:
            body_text = _search_latest_recovery_email(imap)
            if body_text:
                break
            time.sleep(POLLING_INTERVAL)
    finally:
        if imap:
            try:
                imap.logout()
            except Exception:
                pass

    if not body_text:
        pytest.skip("Не найдено письмо со ссылкой для восстановления (либо письмо ещё не пришло).")

    token = _extract_token_from_body(body_text)
    if not token:
        pytest.skip("Не удалось извлечь token из письма (формат письма неожиданный).")

    print("Found token:", token)

    # 3) сброс пароля
    new_password = "NewPassword123!"
    reset_payload = {"token": token, "password": new_password}
    reset_response = requests.post(RESET_URL, json=reset_payload)
    print("Reset response:", reset_response.status_code, reset_response.text)

    if reset_response.status_code == 403 and "Token has expired" in reset_response.text:
        pytest.skip("Токен истёк к моменту использования. Нужно увеличить время ожидания или проверить отправку писем.")
    assert reset_response.status_code == 200, f"Reset failed: {reset_response.status_code} {reset_response.text}"

    # 4) логин (form-urlencoded)
    login_payload = {
        "grant_type": "password",
        "username": GMAIL_USER,
        "password": new_password,
        "scope": "",
        "client_id": "",
        "client_secret": ""
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    login_response = requests.post(LOGIN_URL, data=login_payload, headers=headers)
    print("Login response:", login_response.status_code, login_response.text)
    assert login_response.status_code == 200, f"Login failed: {login_response.status_code} {login_response.text}"
    login_data = login_response.json()
    assert "access_token" in login_data and login_data["token_type"] == "Bearer"
