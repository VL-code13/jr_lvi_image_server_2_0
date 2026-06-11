import psycopg
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()


def get_connection():
    """
    Создаёт и возвращает подключение к базе данных PostgreSQL.
    Использует переменные окружения из файла .env
    """
    return psycopg.connect(
        dbname=os.getenv("DATABASE_NAME"),
        user=os.getenv("DATABASE_USER"),
        password=os.getenv("DATABASE_PASSWORD"),
        host=os.getenv("DATABASE_HOST"),
        port=int(os.getenv("DATABASE_PORT"))  # Конвертируем строку в число
    )
