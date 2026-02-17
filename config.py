# config.py
# Конфигурация для мониторинга интеграций

import os
from dotenv import load_dotenv

load_dotenv()

# ===============================
# 🔹 SMTP настройки (из .env)
# ===============================
SMTP_CONFIG = {
    "server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
    "port": int(os.getenv("SMTP_PORT", "465")),
    "use_ssl": os.getenv("SMTP_USE_SSL", "true").lower() == "true",
    "login": os.getenv("SMTP_LOGIN", ""),
    "password": os.getenv("SMTP_PASSWORD", ""),
}

# ===============================
# 🔹 Получатели уведомлений (из .env)
# ===============================
_recipients = os.getenv("EMAIL_RECIPIENTS", "")
EMAIL_RECIPIENTS = [e.strip() for e in _recipients.split(",") if e.strip()]

# ===============================
# 🔹 Настройки мониторинга
# ===============================
QUICK_CHECK_INTERVAL_MINUTES = 5   # Быстрая проверка (TG при ошибках)
REPORT_INTERVAL_MINUTES = 30       # Полный отчет в Sheets + Email
WORK_HOURS_START = 9               # Начало рабочих часов (9:00)
WORK_HOURS_END = 24                # Конец рабочих часов (00:00 = полночь)

# Для обратной совместимости
CHECK_INTERVAL_MINUTES = QUICK_CHECK_INTERVAL_MINUTES

# ===============================
# 🔹 Часовой пояс (Казахстан)
# ===============================
TIMEZONE = "Asia/Almaty"
