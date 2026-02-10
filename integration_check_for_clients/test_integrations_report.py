from __future__ import annotations

from pathlib import Path
import re
import json
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime

import pytest
import requests

from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv
load_dotenv("/home/zangar_zhunisbekov/integration_checker/.env")


# ===============================
# 🔹 Базовые настройки
# ===============================

BASE_URL = "https://backbackpradavan.city-innovation.kz"

# !!! ВАЖНО: __file__ (у тебя было file)
BASE_DIR = Path(__file__).parent
CLIENT_DATA_PATH = BASE_DIR / "client_data.txt"
SERVICE_ACCOUNT_FILE = BASE_DIR / "service_account.json"

REPORTS_DIR = BASE_DIR.parent / "integration_check_for_clients" / "reports"
SNAPSHOT_FILE = REPORTS_DIR / "last_snapshot.json"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = "11cMzX2cGjaFD-BX9_kdibhUjjvnQMUTyJvWUABKKPKE"

SHEET_LATEST_TITLE = "LATEST"

# ✅ endpoint’ы по твоей доке
INTEGRATION_ENDPOINTS = {
    "telegram": "/api/v1/integrations/telegram",
    "telegram_web": "/api/v1/integrations/telegram_web/status",
    "whatsapp_business": "/api/v1/integrations/whatsapp",
    "waha": "/api/v1/integrations/waha/status",
    "instagram": "/api/v1/integrations/instagram/status",
}

INTEGRATION_KEYS_ORDER = ["telegram", "telegram_web", "whatsapp_business", "waha", "instagram"]
INTEGRATION_NAME_PRETTY = {
    "telegram": "Telegram",
    "telegram_web": "Telegram-Web",
    "whatsapp_business": "WhatsApp Business",
    "waha": "Waha",
    "instagram": "Instagram",
}

# ===============================
# 🔹 Retries для requests
# ===============================

def build_http_session() -> requests.Session:
    """
    Делает retries на: timeout + 502/503/504
    """
    session = requests.Session()
    try:
        from urllib3.util.retry import Retry
        from requests.adapters import HTTPAdapter

        retry = Retry(
            total=3,
            connect=3,
            read=3,
            status=3,
            backoff_factor=0.6,  # 0.6s, 1.2s, 2.4s...
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET", "POST"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
    except Exception:
        # Если вдруг urllib3 Retry недоступен — просто работаем без него.
        pass
    return session


HTTP = build_http_session()

# ===============================
# 🔹 Snapshot (прошлое состояние)
# ===============================

def ensure_reports_dir():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def load_snapshot() -> Dict[str, Dict[str, str]]:
    ensure_reports_dir()
    if SNAPSHOT_FILE.exists():
        return json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    return {}
def save_snapshot(snapshot: Dict[str, Dict[str, str]]) -> None:
    ensure_reports_dir()
    SNAPSHOT_FILE.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

def classify_change(before: str, after: str) -> Optional[str]:
    if before == after:
        return None
    if before == "✅" and after == "❌":
        return "DOWN"
    if before in ("❌", "—") and after == "✅":
        return "UP"
    if before == "✅" and after == "—":
        return "DISABLED"
    return "CHANGED"

# ===============================
# 🔹 Telegram (только по изменениям)
# ===============================
def tg_send(text: str) -> None:
    token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")

    if not token or not chat_id:
        print("TOKEN:", token)
        print("CHAT_ID:", chat_id)

        print("⚠️ TG_BOT_TOKEN / TG_CHAT_ID не заданы — Telegram пропущен")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        HTTP.post(
            url,
            json={"chat_id": chat_id, "text": text},
            timeout=15
        )
    except Exception as e:
        print(f"⚠️ Ошибка отправки в Telegram: {e}")

# ===============================
# 🔹 Клиенты
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


def get_auth_headers(username: str, password: str) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    login_data = {
        "grant_type": "password",
        "username": username,
        "password": password,
        "scope": "",
        "client_id": "",
        "client_secret": ""
    }

    try:
        response = HTTP.post(
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


# ===============================
# 🔹 Интеграции
# ===============================

def map_status_to_emoji(status: Optional[bool], message: Optional[str], http_ok: bool) -> str:
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


def check_integration(endpoint: str, headers: Dict[str, str]) -> tuple[str, Optional[bool], Optional[str]]:
    url = f"{BASE_URL}{endpoint}"
    try:
        resp = HTTP.get(url, headers=headers, timeout=15)
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


def extract_identifier_from_message(integration_name: str, message: Optional[str]) -> Optional[str]:
    if not message:
        return None

    msg = message.strip()
    if not msg:
        return None

    lower_name = integration_name.lower()

    if "telegram" in lower_name:
        m = re.search(r'@[\w_]+', msg)
        if m:
            return m.group(0)

    if "instagram" in lower_name:
        if ":" in msg:
            return msg.split(":", 1)[1].strip()

    if "waha" in lower_name:
        clean = "".join(ch for ch in msg if ch.isdigit() or ch in "+ ")
        clean = clean.strip()
        if clean:
            return clean

    if "error" not in msg.lower():
        return msg

    return None


def build_integration_comment(name: str, emoji: str, status: Optional[bool], message: Optional[str]) -> str:
    if emoji == "—":
        return f"{name}: нет интеграции"

    if emoji == "❌":
        base = f"{name}: ошибка интеграции"
        if message:
            base += f" ({message})"
        return base

    identifier = extract_identifier_from_message(name, message)
    if identifier:
        return f"{name}: {identifier}"
    return f"{name}: есть интеграция"


# ===============================
# 🔹 Google Sheets
# ===============================

def get_sheets_service():
    creds = Credentials.from_service_account_file(str(SERVICE_ACCOUNT_FILE), scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)

def get_or_create_sheet(service, spreadsheet_id: str, title: str) -> int:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sh in meta.get("sheets", []):
        props = sh.get("properties", {})
        if props.get("title") == title:
            return props["sheetId"]

    # создать если нет
    resp = service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [{"addSheet": {"properties": {"title": title}}}]}
    ).execute()
    return resp["replies"][0]["addSheet"]["properties"]["sheetId"]

def clear_sheet(service, spreadsheet_id: str, sheet_title: str):
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_title}'!A:Z",
        body={}
    ).execute()
def reset_sheet_formatting(service, spreadsheet_id: str, sheet_id: int) -> None:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

    target_sheet = None
    for sh in meta.get("sheets", []):
        if sh.get("properties", {}).get("sheetId") == sheet_id:
            target_sheet = sh
            break

    if not target_sheet:
        return

    requests_body = []

    # удалить banding
    for br in (target_sheet.get("bandedRanges") or []):
        br_id = br.get("bandedRangeId")
        if br_id is not None:
            requests_body.append({"deleteBanding": {"bandedRangeId": br_id}})

    # удалить conditional formatting rules (удалять с конца!)
    cond_formats = target_sheet.get("conditionalFormats") or []
    for idx in range(len(cond_formats) - 1, -1, -1):
        requests_body.append({
            "deleteConditionalFormatRule": {
                "sheetId": sheet_id,
                "index": idx
            }
        })

    if requests_body:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests_body}
        ).execute()

def write_report(rows: List[Dict[str, Any]]):
    """
    Пишет отчёт в один лист LATEST (перезаписывает).
    Добавляет колонку "Изменения" (с прошлого запуска).
    Оставляет логин/пароль в отчёте (как ты просила).
    """
    headers = [
        "Название клиента",
        "Логин",
        "Пароль",
        "Telegram",
        "Telegram-Web",
        "WhatsApp Business",
        "Waha",
        "Instagram",
        "Комментарий",
        "Изменения (с прошлого запуска)",
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
            row.get("Waha", ""),
            row.get("Instagram", ""),
            row.get("Комментарий", ""),
            row.get("Изменения", ""),
        ])

    # Легенда
    values.append([])
    values.append([
        "Легенда:",
        "",
        "",
        "✅ — работает",
        "❌ — работает некорректно / не отвечает",
        "— — интеграции нет / не настроено",
        "",
        "",
        "",
        "",
    ])

    service = get_sheets_service()
    sheet_id = get_or_create_sheet(service, SPREADSHEET_ID, SHEET_LATEST_TITLE)

    # очистить и записать заново
    clear_sheet(service, SPREADSHEET_ID, SHEET_LATEST_TITLE)
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{SHEET_LATEST_TITLE}'!A1",
        valueInputOption="RAW",
        body={"values": values}
    ).execute()
    reset_sheet_formatting(service, SPREADSHEET_ID, sheet_id)

    num_data_rows = len(rows)
    num_columns = len(headers)

    # оформление
    requests_body: List[Dict[str, Any]] = []

    # Шапка
    requests_body.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": num_columns},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.75, "green": 0.85, "blue": 0.95},
                "horizontalAlignment": "CENTER",
                "verticalAlignment": "MIDDLE",
                "textFormat": {"bold": True},
            }},
            "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,verticalAlignment,textFormat.bold)"
        }
    })

    # Freeze header
    requests_body.append({
        "updateSheetProperties": {
            "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount"
        }
    })

    # wrap
    requests_body.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 1 + num_data_rows + 3, "startColumnIndex": 0, "endColumnIndex": num_columns},
            "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}},
            "fields": "userEnteredFormat.wrapStrategy"
        }
    })

    # banding
    if num_data_rows > 0:
        requests_body.append({
            "addBanding": {
                "bandedRange": {
                    "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 1 + num_data_rows, "startColumnIndex": 0, "endColumnIndex": num_columns},
                    "rowProperties": {
                        "firstBandColor": {"red": 0.98, "green": 0.98, "blue": 0.98},
                        "secondBandColor": {"red": 0.93, "green": 0.96, "blue": 1.0},
                    }
                }
            }
        })

    # autoresize
    requests_body.append({
        "autoResizeDimensions": {
            "dimensions": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": num_columns}
        }
    })

    # conditional formatting by emoji for status columns D..H
    if num_data_rows > 0:
        status_range = {
            "sheetId": sheet_id,
            "startRowIndex": 1,
            "endRowIndex": 1 + num_data_rows,
            "startColumnIndex": 3,   # D
            "endColumnIndex": 8,     # H
        }

        # ✅
        requests_body.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [status_range],
                    "booleanRule": {
                        "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": "✅"}]},
                        "format": {"backgroundColor": {"red": 0.80, "green": 0.94, "blue": 0.80}}
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
                        "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": "❌"}]},
                        "format": {"backgroundColor": {"red": 0.98, "green": 0.80, "blue": 0.80}}
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
                        "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": "—"}]},
                        "format": {"backgroundColor": {"red": 0.93, "green": 0.93, "blue": 0.93}}
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
    print(f"   Лист: {SHEET_LATEST_TITLE}")


# ===============================
# 🔹 Тест / запуск
# ===============================

@pytest.mark.integration
def test_integration_status_report():
    clients = load_clients()
    total = len(clients)
    assert total > 0, "Нет ни одного клиента в client_data.txt"

    old_snapshot = load_snapshot()
    current_snapshot: Dict[str, Dict[str, str]] = {}

    report_rows: List[Dict[str, Any]] = []
    telegram_changes: List[str] = []

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
                "Waha": "❌",
                "Instagram": "❌",
                "Комментарий": comment,
            }
            # snapshot для сравнения
            current_snapshot[client_name] = {
                "telegram": "❌",
                "telegram_web": "❌",
                "whatsapp_business": "❌",
                "waha": "❌",
                "instagram": "❌",
            }
            row["Изменения"] = ""  # логин-ошибка часто шумит, оставим пусто
            report_rows.append(row)
            continue

        telegram_emoji, telegram_status, telegram_msg = check_integration(INTEGRATION_ENDPOINTS["telegram"], headers)
        telegram_web_emoji, telegram_web_status, telegram_web_msg = check_integration(INTEGRATION_ENDPOINTS["telegram_web"], headers)
        whatsapp_business_emoji, whatsapp_business_status, whatsapp_business_msg = check_integration(INTEGRATION_ENDPOINTS["whatsapp_business"], headers)
        waha_emoji, waha_status, waha_msg = check_integration(INTEGRATION_ENDPOINTS["waha"], headers)
        instagram_emoji, instagram_status, instagram_msg = check_integration(INTEGRATION_ENDPOINTS["instagram"], headers)

        current_snapshot[client_name] = {
            "telegram": telegram_emoji,
            "telegram_web": telegram_web_emoji,
            "whatsapp_business": whatsapp_business_emoji,
            "waha": waha_emoji,
            "instagram": instagram_emoji,
        }

        comment_lines = [
            build_integration_comment("Telegram", telegram_emoji, telegram_status, telegram_msg),
            build_integration_comment("Telegram-Web", telegram_web_emoji, telegram_web_status, telegram_web_msg),
            build_integration_comment("WhatsApp Business", whatsapp_business_emoji, whatsapp_business_status, whatsapp_business_msg),
            build_integration_comment("Waha", waha_emoji, waha_status, waha_msg),
            build_integration_comment("Instagram", instagram_emoji, instagram_status, instagram_msg),
        ]
        comment = "\n".join(comment_lines)

        # ---- diff для Sheets + Telegram ----
        old_row = old_snapshot.get(client_name, {})
        changes_for_client: List[str] = []

        for k in INTEGRATION_KEYS_ORDER:
            before = old_row.get(k, "—")
            after = current_snapshot[client_name].get(k, "—")

            change = classify_change(before, after)
            if not change:
                continue

            pretty = INTEGRATION_NAME_PRETTY[k]
            if change == "UP":
                changes_for_client.append(f"{pretty}: {before}→{after} (появилось)")
                telegram_changes.append(f"{client_name}: {pretty} {before} → {after} (✅ появилось)")
            elif change == "DOWN":
                changes_for_client.append(f"{pretty}: {before}→{after} (упало)")
                telegram_changes.append(f"{client_name}: {pretty} {before} → {after} (❌ упало)")
            elif change == "DISABLED":
                changes_for_client.append(f"{pretty}: {before}→{after} (отключено\убрали)")
                telegram_changes.append(f"{client_name}: {pretty} {before} → {after} (⛔ отключено\убрали)")
            else:
                changes_for_client.append(f"{pretty}: {before}→{after} (изменилось)")
                telegram_changes.append(f"{client_name}: {pretty} {before} → {after} (🔄 изменилось)")

        row = {
            "Название клиента": client_name,
            "Логин": login,
            "Пароль": password,  # как ты просила — оставляем
            "Telegram": telegram_emoji,
            "Telegram-Web": telegram_web_emoji,
            "WhatsApp Business": whatsapp_business_emoji,
            "Waha": waha_emoji,
            "Instagram": instagram_emoji,
            "Комментарий": comment,
            "Изменения": "\n".join(changes_for_client) if changes_for_client else "",
        }
        report_rows.append(row)

    # Сохраняем snapshot для следующего запуска
    save_snapshot(current_snapshot)
    # Пишем в Sheets (в один лист LATEST)
    write_report(report_rows)

    # Telegram — только если есть изменения
    # Telegram — всегда, но с разным текстом
    if telegram_changes:
        text = "🔔 Изменения интеграций:\n" + "\n".join(telegram_changes[:80])
        if len(telegram_changes) > 80:
            text += f"\n… и ещё {len(telegram_changes) - 80}"
        tg_send(text)
    else:
        tg_send("✅ Проверка прошла успешно.\nИзменений в интеграциях нет.")