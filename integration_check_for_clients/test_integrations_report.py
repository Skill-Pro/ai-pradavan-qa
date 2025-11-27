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
SPREADSHEET_ID = "11cMzX2cGjaFD-BX9_kdibhUjjvnQMUTyJvWUABKKPKE"  # <-- обязательно замени

INTEGRATION_ENDPOINTS = {
    "telegram": "/api/v1/integrations/telegram",
    "telegram_web": "/api/v1/integrations/telegram_web/status",
    "whatsapp_business": "/api/v1/integrations/whatsapp",
    "whatsapp_web": "/api/v1/integrations/whatsapp_web/status",
    "instagram": "/api/v1/integrations/instagram/status",
}

# ===============================
# 🔹 Вспомогательные функции
# ===============================

def load_clients() -> List[Tuple[str, str, str]]:
    if not CLIENT_DATA_PATH.exists():
        raise FileNotFoundError(f"Файл с клиентами не найден: {CLIENT_DATA_PATH}")

    clients: List[Tuple[str, str, str]] = []
    with CLIENT_DATA_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 3:
                print(f"⚠️ Пропущена строка (ожидалось 3 колонки): {line}")
                continue
            client_name, login, password = parts[0], parts[1], parts[2]
            clients.append((client_name, login, password))
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

    # WhatsApp
    if "whatsapp" in lower_name:
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


def write_report(rows: List[Dict[str, Any]]):
    """
    Пишет отчет в Google Sheets:
    - новый лист на каждый запуск
    - цветная шапка, зебра-строки
    - цвета по статусам (✅ зелёный, ❌ красный, — серый)
    """
    ensure_reports_dir()

    headers = [
        "название клиент",
        "Логин",
        "Пароль",
        "Telegram",
        "Telegram-Web",
        "WhatsApp Busine",
        "WhatsApp-Web",
        "Instagram",
        "Комментарий",
    ]

    values: List[List[Any]] = [headers]

    for row in rows:
        values.append([
            row.get("Название клиента", ""),
            row.get("Логин", ""),
            row.get("Пароль", ""),
            row.get("Telegram", ""),
            row.get("Telegram-Web", ""),
            row.get("WhatsApp Business", ""),
            row.get("WhatsApp-Web", ""),
            row.get("Instagram", ""),
            row.get("Комментарий", ""),
        ])

    # Легенда
    values.append([])
    values.append([
        "Легенда:",
        "",
        "",
        "✅ — работает"
        "❌ — работает некорректно / не отвечает",
        "— — интеграции нет / не настроено, возможно баг",
        "",
        "",
        "",
    ])

    service = get_sheets_service()

    sheet_title = datetime.now().strftime("Отчет %Y-%m-%d %H:%M")

    # 1) создаём новый лист
    add_sheet_body = {
        "requests": [
            {
                "addSheet": {
                    "properties": {
                        "title": sheet_title,
                        "gridProperties": {
                            "rowCount": len(values) + 20,
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

    # 2) записываем данные
    range_all = f"'{sheet_title}'!A1"
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=range_all,
        valueInputOption="RAW",
        body={"values": values}
    ).execute()

    num_data_rows = len(rows)
    num_columns = len(headers)

    # 3) оформление
    requests_body: List[Dict[str, Any]] = []

    # 3.1. Шапка
    requests_body.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": num_columns,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.75, "green": 0.85, "blue": 0.95},
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                    "textFormat": {"bold": True},
                }
            },
            "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,verticalAlignment,textFormat.bold)"
        }
    })

    # 3.2. Закрепить первую строку
    requests_body.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {
                    "frozenRowCount": 1
                }
            },
            "fields": "gridProperties.frozenRowCount"
        }
    })

    # 3.3. Перенос строк
    requests_body.append({
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1,
                "endRowIndex": 1 + num_data_rows + 3,
                "startColumnIndex": 0,
                "endColumnIndex": num_columns,
            },
            "cell": {
                "userEnteredFormat": {
                    "wrapStrategy": "WRAP"
                }
            },
            "fields": "userEnteredFormat.wrapStrategy"
        }
    })

    # 3.4. Зебра-строки (полоски)
    if num_data_rows > 0:
        requests_body.append({
            "addBanding": {
                "bandedRange": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": 1 + num_data_rows,
                        "startColumnIndex": 0,
                        "endColumnIndex": num_columns,
                    },
                    "rowProperties": {
                        "firstBandColor": {"red": 0.98, "green": 0.98, "blue": 0.98},
                        "secondBandColor": {"red": 0.93, "green": 0.96, "blue": 1.0},
                    }
                }
            }
        })

    # 3.5. Автоширина колонок
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

    # 3.6. Условное форматирование: ✅ зелёный, ❌ красный, — серый
    if num_data_rows > 0:
        status_range = {
            "sheetId": sheet_id,
            "startRowIndex": 1,
            "endRowIndex": 1 + num_data_rows,
            "startColumnIndex": 3,  # D
            "endColumnIndex": 8,  # H
        }

        # ✅
        requests_body.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [status_range],
                    "booleanRule": {
                        "condition": {
                            "type": "TEXT_EQ",
                            "values": [{"userEnteredValue": "✅"}]
                        },
                        "format": {
                            "backgroundColor": {"red": 0.80, "green": 0.94, "blue": 0.80}
                        }
                    }
                },
                "index": 0
            }
        })

        # ❌
        requests_body.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [status_range],
                    "booleanRule": {
                        "condition": {
                            "type": "TEXT_EQ",
                            "values": [{"userEnteredValue": "❌"}]
                        },
                        "format": {
                            "backgroundColor": {"red": 0.98, "green": 0.80, "blue": 0.80}
                        }
                    }
                },
                "index": 0
            }
        })

        # —
        requests_body.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [status_range],
                    "booleanRule": {
                        "condition": {
                            "type": "TEXT_EQ",
                            "values": [{"userEnteredValue": "—"}]
                        },
                        "format": {
                            "backgroundColor": {"red": 0.93, "green": 0.93, "blue": 0.93}
                        }
                    }
                },
                "index": 0
            }
        })

    if requests_body:
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": requests_body}
        ).execute()

    print("\n✅ Отчет по интеграциям сохранен в Google Sheets:")
    print(f"   https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    print(f"   Лист: {sheet_title}")
    print("\nЛегенда:")
    print("  ✅ — работает корректно")
    print("  ❌ — работает некорректно / не отвечает")
    print("  —  — интеграции нет / не настроено, возможно баг")


# ===============================
# 🔹 Один общий тест
# ===============================

@pytest.mark.integration
def test_integration_status_report():
    clients = load_clients()
    total = len(clients)
    assert total > 0, "Нет ни одного клиента в client_data.txt"

    report_rows: List[Dict[str, Any]] = []

    for idx, (client_name, login, password) in enumerate(clients, start=1):
        print(f"[{idx}/{total}] Проверяю клиента: {client_name} ({login})")

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
                "Instagram": "❌",
                "Комментарий": comment,
            }
            report_rows.append(row)
            continue

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

        comment_lines = [
            build_integration_comment("Telegram", telegram_emoji, telegram_status, telegram_msg),
            build_integration_comment("Telegram-Web", telegram_web_emoji, telegram_web_status, telegram_web_msg),
            build_integration_comment("WhatsApp Business", whatsapp_business_emoji, whatsapp_business_status,
                                      whatsapp_business_msg),
            build_integration_comment("WhatsApp Web", whatsapp_web_emoji, whatsapp_web_status, whatsapp_web_msg),
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
            "Instagram": instagram_emoji,
            "Комментарий": comment,
        }
        report_rows.append(row)

    write_report(report_rows)