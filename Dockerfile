# Dockerfile для сервиса мониторинга интеграций

FROM python:3.11-slim

# Установка рабочей директории
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости + pytz для часового пояса
RUN pip install --no-cache-dir -r requirements.txt pytz

# Копируем весь проект
COPY . .

# Устанавливаем часовой пояс
ENV TZ=Asia/Almaty
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Запускаем скрипт мониторинга
CMD ["python", "-u", "run_daily_report.py"]
