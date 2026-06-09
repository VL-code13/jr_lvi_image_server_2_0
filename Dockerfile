FROM python:3.12-slim


# Устанавливаем рабочий каталог
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Создаём папки для изображений и логов, устанавливаем права
RUN mkdir -p /app/images /app/logs && chmod 755 /app/images /app/logs

# Указываем порт, который будет открыт
EXPOSE 3000

# Команда для запуска приложения
CMD ["python", "app.py"]
