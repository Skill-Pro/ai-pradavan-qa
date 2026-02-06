from pathlib import Path
import os
import re
from typing import List, Tuple, Dict, Any
from datetime import datetime

import pytest
import requests

from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from pathlib import Path

# ===============================
# 🔹 Базовые настройки
# ===============================

BASE_URL = "https://backbackpradavan.city-innovation.kz"
CLIENT_DATA_PATH = Path(__file__).parent / "client_data.txt"

REPORTS_DIR = Path(__file__).parent.parent / "integration_check_for_clients" / "reports"

SERVICE_ACCOUNT_FILE = Path(__file__).parent / "service_account.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "17Z5CGL5kI3b-5R2mRF8R3rRUbZkwDdhuY1kaAcWWKfs"

INTEGRATION_ENDPOINTS = {
    "telegram": "/api/v1/integrations/telegram",
    "telegram_web": "/api/v1/integrations/telegram_web/status",
    "whatsapp_business": "/api/v1/integrations/whatsapp",
    "whatsapp_web": "/api/v1/integrations/whatsapp_web/status",
    "instagram": "/api/v1/integrations/instagram/status",
    "waha": "/api/v1/integrations/waha/status",
    "wazzup": "/api/v1/integrations/wazzup/status",
}

# ===============================
# 🔹 Вспомогательные функции
# ===============================

def load_clients() -> Dict[str, List[Tuple[str, str, str]]]:
    """
    Загружает клиентов из файла с разделением по категориям.
    
    Returns:
        Dict с ключами 'КАСТОМНЫЕ' и 'ПЛАТФОРМА', значения — списки (имя, логин, пароль)
    """
    if not CLIENT_DATA_PATH.exists():
        raise FileNotFoundError(f"Файл с клиентами не найден: {CLIENT_DATA_PATH}")

    clients: Dict[str, List[Tuple[str, str, str]]] = {
        "КАСТОМНЫЕ": [],
        "ПЛАТФОРМА": []
    }
    current_category = "КАСТОМНЫЕ"  # по умолчанию
    
    with CLIENT_DATA_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Проверяем маркеры категорий
            if line.startswith("# КАСТОМНЫЕ"):
                current_category = "КАСТОМНЫЕ"
                continue
            elif line.startswith("# ПЛАТФОРМА"):
                current_category = "ПЛАТФОРМА"
                continue
            elif line.startswith("#"):
                continue
            
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 3:
                print(f"⚠️ Пропущена строка (ожидалось 3 колонки): {line}")
                continue
            client_name, login, password = parts[0], parts[1], parts[2]
            clients[current_category].append((client_name, login, password))
    
    return clients


def get_auth_headers(username: str, password: str) -> Tuple[Dict[str, str] | None, str | None]:
    login_data = {
        "grant_type": "password",
        "username": username,
        "password": password,
        "scope": "",
        "client_id": "",
        "client_secret": ""
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            data=login_data,
            headers={"accept": "application/json"},
            timeout=15,
        )
    except Exception as e:
        return None, f"Ошибка запроса логина: {e}"

    if response.status_code != 200:
        return None, f"Ошибка авторизации ({response.status_code}): {response.text}"

    token_data = response.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return None, f"Токен не найден в ответе: {response.text}"

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    return headers, None


def map_status_to_emoji(status: bool | None, message: str | None, http_ok: bool) -> str:
    """
    ✅ — работает корректно
    ❌ — ошибка / некорректная работа
    —  — интеграции нет / не настроено
    """
    if not http_ok:
        return "❌"

    msg = (message or "").lower()

    if status is True:
        return "✅"

    # типичные тексты «нет интеграции»
    if any(kw in msg for kw in [
        "not found",
        "no telegram web integration",
        "integration not configured",
        "integration not found",
        "not configured"
    ]):
        return "—"

    if status is False and not msg:
        return "—"

    return "❌"


def check_integration(endpoint: str, headers: Dict[str, str]) -> tuple[str, bool | None, str | None]:
    """
    Делает GET к endpoint и возвращает:
    (emoji_status, status_bool, message_string)
    """
    url = f"{BASE_URL}{endpoint}"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
    except Exception as e:
        return "❌", None, f"request_error: {e}"

    http_ok = resp.status_code == 200
    if not http_ok:
        text = resp.text
        emoji = map_status_to_emoji(False, text, http_ok)
        return emoji, None, text

    try:
        data = resp.json()
    except Exception as e:
        return "❌", None, f"json_error: {e}"

    status = data.get("status")
    message = data.get("message")
    emoji = map_status_to_emoji(status, message, http_ok)

    return emoji, status, message


def extract_identifier_from_message(integration_name: str, message: str | None) -> str | None:
    """
    Достаёт ник / номер из message по правилам для разных интеграций.
    Работает с такими примерами:

    Instagram: "Username: zakow05"           → "zakow05"
    WhatsApp Web: "77075582005"             → "77075582005"
    Telegram: "Bot name: ..., username: @..."→ "@..."
    """
    if not message:
        return None

    msg = message.strip()
    if not msg:
        return None

    lower_name = integration_name.lower()

    # Telegram / Telegram-Web
    if "telegram" in lower_name:
        # пробуем найти @username
        m = re.search(r'@[\w_]+', msg)
        if m:
            return m.group(0)
        # если нет @, но есть "username:"
        if "username" in msg.lower():
            part = msg.lower().split("username", 1)[1]
            part = part.replace(":", " ").strip()
            if part:
                first = part.split()[0]
                if not first.startswith("@"):
                    first = "@" + first
                return first

    # Instagram
    if "instagram" in lower_name:
        # "Username: zakow05"
        if ":" in msg:
            return msg.split(":", 1)[1].strip()

    # WhatsApp (включая WAHA/WAZZUP)
    if "whatsapp" in lower_name or "waha" in lower_name or "wazzup" in lower_name:
        # из строки оставляем цифры и +/пробел
        clean = "".join(ch for ch in msg if ch.isdigit() or ch in "+ ")
        clean = clean.strip()
        if clean:
            return clean

    # если ничего спец. не нашли и текст не похож на ошибку —
    # можно вернуть весь message (но лучше не для ошибок)
    if "error" not in msg.lower():
        return msg

    return None


def build_integration_comment(
    name: str,
    emoji: str,
    status: bool | None,
    message: str | None,
) -> str:
    """
    Возвращает строку:
    - "Telegram: нет интеграции"
    - "Telegram: @nickname"
    - "WhatsApp Web: 7707..."
    - "Telegram-Web: ошибка интеграции (текст)"
    """
    # Нет интеграции
    if emoji == "—":
        return f"{name}: нет интеграции"

    # Ошибка
    if emoji == "❌":
        base = f"{name}: ошибка интеграции"
        if message:
            base += f" ({message})"
        return base

    # ✅ — интеграция есть, вытаскиваем идентификатор
    identifier = extract_identifier_from_message(name, message)

    if identifier:
        return f"{name}: {identifier}"

    return f"{name}: есть интеграция"


def ensure_reports_dir():
    if not REPORTS_DIR.exists():
        os.makedirs(REPORTS_DIR, exist_ok=True)


def get_sheets_service():
    creds = Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE),
        scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=creds)
    return service


def write_report(custom_rows: List[Dict[str, Any]], platform_rows: List[Dict[str, Any]]):
    """
    Пишет отчет в Google Sheets во вкладку "Статусы YYYY-MM-DD":
    - отдельная вкладка на каждый день
    - разделение на секции КАСТОМНЫЕ и ПЛАТФОРМА
    - данные добавляются блоками с указанием времени
    """
    ensure_reports_dir()

    headers = [
        "№",
        "Клиент",
        "Логин",
        "Telegram",
        "Telegram-Web",
        "WhatsApp Business",
        "WhatsApp-Web",
        "WAHA",
        "WAZZUP",
        "Instagram",
        "Статус",
    ]

    service = get_sheets_service()
    
    today = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M")
    
    # Название вкладки = "Статусы" + дата
    sheet_name = f"Статусы {today}"
    
    # Проверяем, существует ли вкладка
    spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    sheets = spreadsheet.get("sheets", [])
    
    sheet_exists = False
    sheet_id = None
    
    for sheet in sheets:
        if sheet["properties"]["title"] == sheet_name:
            sheet_exists = True
            sheet_id = sheet["properties"]["sheetId"]
            break
    
    # Если вкладки нет — создаём
    if not sheet_exists:
        add_sheet_body = {
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": sheet_name,
                            "gridProperties": {
                                "rowCount": 5000,
                                "columnCount": len(headers)
                            }
                        }
                    }
                }
            ]
        }
        add_sheet_response = service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=add_sheet_body
        ).execute()
        sheet_id = add_sheet_response["replies"][0]["addSheet"]["properties"]["sheetId"]
        
        # Добавляем заголовок и легенду в самый верх
        legend = [
            [f"📊 Мониторинг интеграций | {today}"],
            [""],
            ["Легенда: ✅ работает | ❌ ошибка/не отвечает | — нет интеграции"],
            [""],
        ]
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{sheet_name}'!A1",
            valueInputOption="RAW",
            body={"values": legend}
        ).execute()
    
    # Получаем текущее количество строк
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{sheet_name}'!A:A"
    ).execute()
    existing_rows = len(result.get("values", []))
    
    # Формируем блок данных
    values: List[List[Any]] = []
    
    # Временная метка
    values.append([""])
    values.append([f"════════════════════════════════════════════════════════"])
    values.append([f"⏰ ПРОВЕРКА В {current_time}"])
    values.append([f"════════════════════════════════════════════════════════"])
    values.append([""])
    
    # Подсчет статистики
    total_custom = len(custom_rows)
    total_platform = len(platform_rows)
    
    # --- КАСТОМНЫЕ ---
    if custom_rows:
        problems_custom = sum(1 for r in custom_rows if "❌" in str(r.values()))
        values.append([f"📦 КАСТОМНЫЕ РЕШЕНИЯ ({total_custom} клиентов, проблем: {problems_custom})"])
        values.append(headers)
        for idx, row in enumerate(custom_rows, 1):
            # Определяем статус
            statuses = [row.get("Telegram", ""), row.get("Telegram-Web", ""),
                       row.get("WhatsApp Business", ""), row.get("WhatsApp-Web", ""),
                       row.get("WAHA", ""), row.get("WAZZUP", ""),
                       row.get("Instagram", "")]
            if "❌" in statuses:
                status = "⚠️ Есть проблемы"
            elif all(s == "✅" for s in statuses if s):
                status = "✅ Всё работает"
            else:
                status = "ℹ️ Частично"
            
            values.append([
                idx,
                row.get("Название клиента", ""),
                row.get("Логин", ""),
                row.get("Telegram", ""),
                row.get("Telegram-Web", ""),
                row.get("WhatsApp Business", ""),
                row.get("WhatsApp-Web", ""),
                row.get("WAHA", ""),
                row.get("WAZZUP", ""),
                row.get("Instagram", ""),
                status,
            ])
        values.append([""])
    
    # --- ПЛАТФОРМА ---
    if platform_rows:
        problems_platform = sum(1 for r in platform_rows if "❌" in str(r.values()))
        values.append([f"🌐 ПЛАТФОРМА ({total_platform} клиентов, проблем: {problems_platform})"])
        values.append(headers)
        for idx, row in enumerate(platform_rows, 1):
            # Определяем статус
            statuses = [row.get("Telegram", ""), row.get("Telegram-Web", ""),
                       row.get("WhatsApp Business", ""), row.get("WhatsApp-Web", ""),
                       row.get("WAHA", ""), row.get("WAZZUP", ""),
                       row.get("Instagram", "")]
            if "❌" in statuses:
                status = "⚠️ Есть проблемы"
            elif all(s == "✅" for s in statuses if s):
                status = "✅ Всё работает"
            else:
                status = "ℹ️ Частично"
            
            values.append([
                idx,
                row.get("Название клиента", ""),
                row.get("Логин", ""),
                row.get("Telegram", ""),
                row.get("Telegram-Web", ""),
                row.get("WhatsApp Business", ""),
                row.get("WhatsApp-Web", ""),
                row.get("WAHA", ""),
                row.get("WAZZUP", ""),
                row.get("Instagram", ""),
                status,
            ])
    
    values.append([""])
    
    # Записываем данные
    start_row = existing_rows + 1
    range_to_write = f"'{sheet_name}'!A{start_row}"
    
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=range_to_write,
        valueInputOption="RAW",
        body={"values": values}
    ).execute()
    
    # Оформление
    num_columns = len(headers)
    requests_body: List[Dict[str, Any]] = []
    
    # Автоширина колонок
    requests_body.append({
        "autoResizeDimensions": {
            "dimensions": {
                "sheetId": sheet_id,
                "dimension": "COLUMNS",
                "startIndex": 0,
                "endIndex": num_columns
            }
        }
    })
    
    if requests_body:
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": requests_body}
        ).execute()

    print(f"\n✅ Отчет добавлен в Google Sheets:")
    print(f"   https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    print(f"   Вкладка: {sheet_name} | Время: {current_time}")


# ===============================
# 🔹 Один общий тест
# ===============================

def check_client(client_name: str, login: str, password: str) -> Tuple[Dict[str, Any], Dict[str, Any] | None]:
    """
    Проверяет одного клиента и возвращает (row, problem или None)
    """
    headers, login_error = get_auth_headers(login, password)

    if headers is None:
        comment = "Ошибка логина: " + (login_error or "")
        row = {
            "Название клиента": client_name,
            "Логин": login,
            "Пароль": password,
            "Telegram": "❌",
            "Telegram-Web": "❌",
            "WhatsApp Business": "❌",
            "WhatsApp-Web": "❌",
            "WAHA": "❌",
            "WAZZUP": "❌",
            "Instagram": "❌",
            "Комментарий": comment,
        }
        problem = {
            "name": client_name,
            "login": login,
            "problems": {"Авторизация": "Ошибка логина"},
            "comment": comment
        }
        return row, problem

    telegram_emoji, telegram_status, telegram_msg = check_integration(
        INTEGRATION_ENDPOINTS["telegram"], headers
    )
    telegram_web_emoji, telegram_web_status, telegram_web_msg = check_integration(
        INTEGRATION_ENDPOINTS["telegram_web"], headers
    )
    whatsapp_business_emoji, whatsapp_business_status, whatsapp_business_msg = check_integration(
        INTEGRATION_ENDPOINTS["whatsapp_business"], headers
    )
    whatsapp_web_emoji, whatsapp_web_status, whatsapp_web_msg = check_integration(
        INTEGRATION_ENDPOINTS["whatsapp_web"], headers
    )
    instagram_emoji, instagram_status, instagram_msg = check_integration(
        INTEGRATION_ENDPOINTS["instagram"], headers
    )
    waha_emoji, waha_status, waha_msg = check_integration(
        INTEGRATION_ENDPOINTS["waha"], headers
    )
    wazzup_emoji, wazzup_status, wazzup_msg = check_integration(
        INTEGRATION_ENDPOINTS["wazzup"], headers
    )

    comment_lines = [
        build_integration_comment("Telegram", telegram_emoji, telegram_status, telegram_msg),
        build_integration_comment("Telegram-Web", telegram_web_emoji, telegram_web_status, telegram_web_msg),
        build_integration_comment("WhatsApp Business", whatsapp_business_emoji, whatsapp_business_status, whatsapp_business_msg),
        build_integration_comment("WhatsApp Web", whatsapp_web_emoji, whatsapp_web_status, whatsapp_web_msg),
        build_integration_comment("WAHA", waha_emoji, waha_status, waha_msg),
        build_integration_comment("WAZZUP", wazzup_emoji, wazzup_status, wazzup_msg),
        build_integration_comment("Instagram", instagram_emoji, instagram_status, instagram_msg),
    ]
    comment = "\n".join(comment_lines)

    row = {
        "Название клиента": client_name,
        "Логин": login,
        "Пароль": password,
        "Telegram": telegram_emoji,
        "Telegram-Web": telegram_web_emoji,
        "WhatsApp Business": whatsapp_business_emoji,
        "WhatsApp-Web": whatsapp_web_emoji,
        "WAHA": waha_emoji,
        "WAZZUP": wazzup_emoji,
        "Instagram": instagram_emoji,
        "Комментарий": comment,
    }

    # Проверяем на проблемы (❌)
    problems = {}
    if telegram_emoji == "❌":
        problems["Telegram"] = telegram_msg or "ошибка"
    if telegram_web_emoji == "❌":
        problems["Telegram-Web"] = telegram_web_msg or "ошибка"
    if whatsapp_business_emoji == "❌":
        problems["WhatsApp Business"] = whatsapp_business_msg or "ошибка"
    if whatsapp_web_emoji == "❌":
        problems["WhatsApp-Web"] = whatsapp_web_msg or "ошибка"
    if waha_emoji == "❌":
        problems["WAHA"] = waha_msg or "ошибка"
    if wazzup_emoji == "❌":
        problems["WAZZUP"] = wazzup_msg or "ошибка"
    if instagram_emoji == "❌":
        problems["Instagram"] = instagram_msg or "ошибка"
    
    problem = None
    if problems:
        problem = {
            "name": client_name,
            "login": login,
            "problems": problems,
            "comment": comment
        }
    
    return row, problem


@pytest.mark.integration
def test_integration_status_report():
    """Pytest-тест для проверки интеграций"""
    clients_by_category = load_clients()
    
    custom_clients = clients_by_category.get("КАСТОМНЫЕ", [])
    platform_clients = clients_by_category.get("ПЛАТФОРМА", [])
    total = len(custom_clients) + len(platform_clients)
    
    assert total > 0, "Нет ни одного клиента в client_data.txt"

    custom_rows: List[Dict[str, Any]] = []
    platform_rows: List[Dict[str, Any]] = []
    
    idx = 0
    
    # Проверяем кастомных
    for client_name, login, password in custom_clients:
        idx += 1
        print(f"[{idx}/{total}] [КАСТОМНЫЕ] {client_name} ({login})")
        row, _ = check_client(client_name, login, password)
        custom_rows.append(row)
    
    # Проверяем платформенных
    for client_name, login, password in platform_clients:
        idx += 1
        print(f"[{idx}/{total}] [ПЛАТФОРМА] {client_name} ({login})")
        row, _ = check_client(client_name, login, password)
        platform_rows.append(row)

    write_report(custom_rows, platform_rows)


def run_integration_check() -> tuple[list[dict], list[dict], list[dict]]:
    """
    Запускает проверку интеграций и возвращает результаты.
    
    Returns:
        tuple: (custom_rows, platform_rows, problem_clients)
    """
    clients_by_category = load_clients()
    
    custom_clients = clients_by_category.get("КАСТОМНЫЕ", [])
    platform_clients = clients_by_category.get("ПЛАТФОРМА", [])
    total = len(custom_clients) + len(platform_clients)
    
    if total == 0:
        print("⚠️ Нет ни одного клиента в client_data.txt")
        return [], [], []

    custom_rows: List[Dict[str, Any]] = []
    platform_rows: List[Dict[str, Any]] = []
    problem_clients: List[Dict[str, Any]] = []
    
    idx = 0
    
    # Проверяем кастомных
    for client_name, login, password in custom_clients:
        idx += 1
        print(f"[{idx}/{total}] [КАСТОМНЫЕ] {client_name} ({login})")
        row, problem = check_client(client_name, login, password)
        custom_rows.append(row)
        if problem:
            problem_clients.append(problem)
    
    # Проверяем платформенных
    for client_name, login, password in platform_clients:
        idx += 1
        print(f"[{idx}/{total}] [ПЛАТФОРМА] {client_name} ({login})")
        row, problem = check_client(client_name, login, password)
        platform_rows.append(row)
        if problem:
            problem_clients.append(problem)

    write_report(custom_rows, platform_rows)
    
    return custom_rows, platform_rows, problem_clients