"""
Скрипт мониторинга интеграций клиентов.
Запускается каждые 30 минут в рабочие часы (9:00 - 00:00).
При обнаружении проблем отправляет email уведомления.
"""

import time
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

try:
    import pytz
    HAS_PYTZ = True
except ImportError:
    HAS_PYTZ = False

from config import (
    SMTP_CONFIG,
    EMAIL_RECIPIENTS,
    CHECK_INTERVAL_MINUTES,
    WORK_HOURS_START,
    WORK_HOURS_END,
    TIMEZONE,
)
from integration_check_for_clients.test_integrations_report import run_integration_check

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


def get_current_hour() -> int:
    """Получить текущий час в нужном часовом поясе."""
    if HAS_PYTZ:
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
    else:
        now = datetime.now()
    return now.hour


def is_working_hours() -> bool:
    """Проверить, находимся ли в рабочих часах."""
    hour = get_current_hour()
    # Если WORK_HOURS_END = 24, то работаем с 9:00 до 23:59
    if WORK_HOURS_END == 24:
        return hour >= WORK_HOURS_START
    return WORK_HOURS_START <= hour < WORK_HOURS_END


def send_email_notification(problem_clients: list) -> bool:
    """
    Отправить email уведомление о проблемных клиентах.
    """
    if not problem_clients:
        return True
    
    if not EMAIL_RECIPIENTS:
        logger.warning("Список получателей пуст, email не отправлен")
        return False

    now = datetime.now()
    date_str = now.strftime('%d.%m.%Y')
    time_str = now.strftime('%H:%M')
    
    # Формируем HTML письмо
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

    # Создаем письмо
    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_CONFIG["login"]
    msg["To"] = ", ".join(EMAIL_RECIPIENTS)
    msg["Subject"] = subject
    
    # Добавляем HTML версию
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


def run_check_cycle():
    """Выполнить один цикл проверки."""
    logger.info("=" * 60)
    logger.info("🚀 Запуск проверки интеграций...")
    
    try:
        # Запускаем проверку и получаем результаты
        custom_rows, platform_rows, problem_clients = run_integration_check()
        
        total_clients = len(custom_rows) + len(platform_rows)
        problem_count = len(problem_clients)
        
        logger.info(f"📊 Проверено клиентов: {total_clients}")
        logger.info(f"⚠️ Клиентов с проблемами: {problem_count}")
        
        if problem_clients:
            logger.info("📧 Отправка уведомлений...")
            send_email_notification(problem_clients)
        else:
            logger.info("✅ Все интеграции работают корректно")
        
        logger.info("✅ Проверка завершена")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке: {e}")
        # Попробуем отправить уведомление об ошибке
        try:
            error_client = [{
                "name": "SYSTEM ERROR",
                "login": "N/A",
                "problems": {"Ошибка системы": str(e)},
                "comment": "Ошибка при выполнении проверки интеграций"
            }]
            send_email_notification(error_client)
        except:
            pass


def main():
    """Основной цикл мониторинга."""
    logger.info("=" * 60)
    logger.info("🔄 Запуск сервиса мониторинга интеграций")
    logger.info(f"⏰ Интервал проверки: {CHECK_INTERVAL_MINUTES} минут")
    logger.info(f"🕐 Рабочие часы: {WORK_HOURS_START}:00 - {WORK_HOURS_END}:00")
    logger.info(f"📧 Получатели: {', '.join(EMAIL_RECIPIENTS)}")
    logger.info("=" * 60)
    
    while True:
        if is_working_hours():
            run_check_cycle()
        else:
            hour = get_current_hour()
            logger.info(f"💤 Вне рабочих часов ({hour}:00). Ожидание...")
        
        # Ждём до следующей проверки
        sleep_seconds = CHECK_INTERVAL_MINUTES * 60
        logger.info(f"⏳ Следующая проверка через {CHECK_INTERVAL_MINUTES} минут...")
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()