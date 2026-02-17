"""
Скрипт мониторинга интеграций клиентов.

Логика работы:
- Проверка каждые 5 минут
- При новых ошибках — мгновенное уведомление в Telegram
- Полный отчет в Google Sheets + Email — каждые 30 минут
- Если всё ОК — тишина (не спамим)
"""

import time
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Set, Dict, Any

try:
    import pytz
    HAS_PYTZ = True
except ImportError:
    HAS_PYTZ = False

from config import (
    SMTP_CONFIG,
    EMAIL_RECIPIENTS,
    QUICK_CHECK_INTERVAL_MINUTES,
    REPORT_INTERVAL_MINUTES,
    WORK_HOURS_START,
    WORK_HOURS_END,
    TIMEZONE,
)
from integration_check_for_clients.test_integrations_report import (
    run_integration_check_silent,
    write_report,
    tg_send,
)

# ===============================
# 🔹 Настройка логирования
# ===============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("monitor.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Хранилище предыдущих проблем (для отслеживания изменений)
previous_problems: Set[str] = set()
last_report_time: datetime = datetime.min


def get_current_time() -> datetime:
    """Получить текущее время в нужном часовом поясе."""
    if HAS_PYTZ:
        tz = pytz.timezone(TIMEZONE)
        return datetime.now(tz)
    return datetime.now()


def get_current_hour() -> int:
    """Получить текущий час в нужном часовом поясе."""
    return get_current_time().hour


def is_working_hours() -> bool:
    """Проверить, находимся ли в рабочих часах."""
    hour = get_current_hour()
    if WORK_HOURS_END == 24:
        return hour >= WORK_HOURS_START
    return WORK_HOURS_START <= hour < WORK_HOURS_END


def problems_to_keys(problem_clients: list) -> Set[str]:
    """Преобразовать список проблем в множество ключей для сравнения."""
    keys = set()
    for p in problem_clients:
        name = p.get("name", "")
        for integration in p.get("problems", {}).keys():
            keys.add(f"{name}:{integration}")
    return keys


def send_email_notification(problem_clients: list) -> bool:
    """Отправить email уведомление о проблемных клиентах."""
    if not problem_clients:
        return True
    
    if not EMAIL_RECIPIENTS:
        logger.warning("Список получателей пуст, email не отправлен")
        return False

    now = datetime.now()
    date_str = now.strftime('%d.%m.%Y')
    time_str = now.strftime('%H:%M')
    
    subject = f"⚠️ Проблемы с интеграциями | {date_str} {time_str}"
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            h2 {{ color: #d32f2f; }}
            table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
            th {{ background-color: #1976d2; color: white; padding: 12px; text-align: left; }}
            td {{ border: 1px solid #ddd; padding: 10px; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .error {{ color: #d32f2f; font-weight: bold; }}
            .footer {{ margin-top: 20px; padding-top: 15px; border-top: 1px solid #ddd; color: #666; }}
            .btn {{ display: inline-block; padding: 10px 20px; background: #1976d2; color: white; text-decoration: none; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h2>⚠️ Обнаружены проблемы с интеграциями</h2>
        
        <p><strong>Дата:</strong> {date_str}<br>
        <strong>Время проверки:</strong> {time_str}<br>
        <strong>Кол-во клиентов с проблемами:</strong> {len(problem_clients)}</p>
        
        <table>
            <tr>
                <th>Клиент</th>
                <th>Логин</th>
                <th>Проблемные интеграции</th>
            </tr>
    """
    
    for client in problem_clients:
        problems_list = "<br>".join([
            f"<span class='error'>❌ {k}</span>" 
            for k in client.get("problems", {}).keys()
        ])
        
        html_body += f"""
            <tr>
                <td><strong>{client['name']}</strong></td>
                <td>{client['login']}</td>
                <td>{problems_list}</td>
            </tr>
        """
    
    html_body += f"""
        </table>
        
        <div class="footer">
            <p>📊 <a href="https://docs.google.com/spreadsheets/d/17Z5CGL5kI3b-5R2mRF8R3rRUbZkwDdhuY1kaAcWWKfs" class="btn">Открыть полный отчёт в Google Sheets</a></p>
            <p style="color: #999; font-size: 12px;">Это автоматическое уведомление от системы мониторинга интеграций AI Pradavan</p>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_CONFIG["login"]
    msg["To"] = ", ".join(EMAIL_RECIPIENTS)
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if SMTP_CONFIG["use_ssl"]:
            server = smtplib.SMTP_SSL(SMTP_CONFIG["server"], SMTP_CONFIG["port"])
        else:
            server = smtplib.SMTP(SMTP_CONFIG["server"], SMTP_CONFIG["port"])
            server.starttls()
        
        server.login(SMTP_CONFIG["login"], SMTP_CONFIG["password"])
        server.sendmail(SMTP_CONFIG["login"], EMAIL_RECIPIENTS, msg.as_string())
        server.quit()
        
        logger.info(f"✅ Email отправлен на: {', '.join(EMAIL_RECIPIENTS)}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки email: {e}")
        return False


def send_full_tg_report(custom_rows: list, platform_rows: list):
    """
    Отправляет полный отчет в Telegram (как в Google Sheets).
    """
    from datetime import datetime
    now = datetime.now()
    time_str = now.strftime('%H:%M')
    date_str = now.strftime('%d.%m.%Y')
    
    lines = [f"📊 Отчет интеграций | {date_str} {time_str}", ""]
    
    # КАСТОМНЫЕ
    if custom_rows:
        ok_count = sum(1 for r in custom_rows if r.get("Статус", "").startswith("✅"))
        lines.append(f"📦 КАСТОМНЫЕ ({len(custom_rows)} клиентов, ✅ {ok_count}):")
        for row in custom_rows:
            name = row.get("Название клиента", "?")
            # Собираем статусы каналов
            channels = []
            for ch in ["Telegram", "Telegram-Web", "WAHA", "Instagram"]:
                val = row.get(ch, "")
                if val == "✅":
                    channels.append(f"{ch}✅")
                elif val == "—":
                    channels.append(f"{ch}—")
                elif val == "❌":
                    channels.append(f"{ch}❌")
            if channels:
                lines.append(f"  • {name}: {', '.join(channels)}")
        lines.append("")
    
    # ПЛАТФОРМА
    if platform_rows:
        ok_count = sum(1 for r in platform_rows if r.get("Статус", "").startswith("✅"))
        lines.append(f"🌐 ПЛАТФОРМА ({len(platform_rows)} клиентов, ✅ {ok_count}):")
        for row in platform_rows:
            name = row.get("Название клиента", "?")
            channels = []
            for ch in ["Telegram", "Telegram-Web", "WAHA", "Instagram"]:
                val = row.get(ch, "")
                if val == "✅":
                    channels.append(f"{ch}✅")
                elif val == "—":
                    channels.append(f"{ch}—")
                elif val == "❌":
                    channels.append(f"{ch}❌")
            if channels:
                lines.append(f"  • {name}: {', '.join(channels)}")
    
    text = "\n".join(lines)
    
    # Telegram ограничение 4096 символов
    if len(text) > 4000:
        text = text[:4000] + "\n... (обрезано)"
    
    tg_send(text)
    logger.info("📱 TG: полный отчет отправлен")


def run_quick_check():
    """
    Быстрая проверка (каждые 5 минут).
    Отправляет в Telegram только при НОВЫХ проблемах.
    """
    global previous_problems
    
    logger.info("-" * 40)
    logger.info("🔍 Быстрая проверка...")
    
    try:
        custom_rows, platform_rows, problem_clients = run_integration_check_silent()
        
        total_clients = len(custom_rows) + len(platform_rows)
        problem_count = len(problem_clients)
        
        logger.info(f"📊 Проверено: {total_clients} | Проблем: {problem_count}")
        
        # Сравниваем с предыдущими проблемами
        current_problems = problems_to_keys(problem_clients)
        new_problems = current_problems - previous_problems
        fixed_problems = previous_problems - current_problems
        
        # Уведомляем только о НОВЫХ проблемах
        if new_problems:
            new_problem_clients = [
                p for p in problem_clients
                if any(f"{p['name']}:{integ}" in new_problems 
                       for integ in p.get("problems", {}).keys())
            ]
            
            if new_problem_clients:
                problems_text = "\n".join([
                    f"🆕 {p['name']}: {', '.join(p['problems'].keys())}\n   📧 {p['login']} | 🔑 {p.get('password', '?')}"
                    for p in new_problem_clients[:15]
                ])
                text = f"🚨 НОВЫЕ проблемы ({len(new_problem_clients)}):\n{problems_text}"
                tg_send(text)
                logger.info(f"📱 TG: отправлено уведомление о {len(new_problem_clients)} новых проблемах")
        
        # Уведомляем о восстановленных (опционально)
        if fixed_problems and not current_problems:
            tg_send("✅ Все интеграции восстановлены!")
            logger.info("📱 TG: все проблемы исправлены")
        
        # Обновляем состояние
        previous_problems = current_problems
        
        return custom_rows, platform_rows, problem_clients
        
    except Exception as e:
        logger.error(f"❌ Ошибка быстрой проверки: {e}")
        return [], [], []


def run_full_report():
    """
    Полный отчет (каждые 30 минут).
    Записывает в Google Sheets + Telegram + Email при проблемах.
    """
    global last_report_time
    
    logger.info("=" * 60)
    logger.info("📋 Полный отчет...")
    
    try:
        custom_rows, platform_rows, problem_clients = run_integration_check_silent()
        
        total_clients = len(custom_rows) + len(platform_rows)
        problem_count = len(problem_clients)
        
        # Записываем в Google Sheets
        write_report(custom_rows, platform_rows)
        
        logger.info(f"📊 Проверено клиентов: {total_clients}")
        logger.info(f"⚠️ Клиентов с проблемами: {problem_count}")
        
        # Полный отчет в Telegram
        send_full_tg_report(custom_rows, platform_rows)
        
        # Email только если есть проблемы
        if problem_clients:
            logger.info("📧 Отправка email...")
            send_email_notification(problem_clients)
        else:
            logger.info("✅ Все интеграции работают корректно")
        
        last_report_time = get_current_time()
        logger.info("✅ Полный отчет завершен")
        
    except Exception as e:
        logger.error(f"❌ Ошибка полного отчета: {e}")


def should_run_full_report() -> bool:
    """Проверить, пора ли делать полный отчет."""
    global last_report_time
    now = get_current_time()
    
    # Первый запуск
    if last_report_time == datetime.min:
        return True
    
    # Прошло достаточно времени
    elapsed_minutes = (now - last_report_time).total_seconds() / 60
    return elapsed_minutes >= REPORT_INTERVAL_MINUTES


def main():
    """Основной цикл мониторинга."""
    global last_report_time
    
    logger.info("=" * 60)
    logger.info("🔄 Запуск сервиса мониторинга интеграций")
    logger.info(f"⚡ Быстрая проверка: каждые {QUICK_CHECK_INTERVAL_MINUTES} мин")
    logger.info(f"📋 Полный отчет: каждые {REPORT_INTERVAL_MINUTES} мин")
    logger.info(f"🕐 Рабочие часы: {WORK_HOURS_START}:00 - {WORK_HOURS_END}:00")
    logger.info(f"📧 Получатели: {', '.join(EMAIL_RECIPIENTS)}")
    logger.info("=" * 60)
    
    while True:
        if is_working_hours():
            # Определяем тип проверки
            if should_run_full_report():
                run_full_report()
            else:
                run_quick_check()
        else:
            hour = get_current_hour()
            logger.info(f"💤 Вне рабочих часов ({hour}:00). Ожидание...")
        
        # Ждём до следующей проверки
        sleep_seconds = QUICK_CHECK_INTERVAL_MINUTES * 60
        logger.info(f"⏳ Следующая проверка через {QUICK_CHECK_INTERVAL_MINUTES} мин...")
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()