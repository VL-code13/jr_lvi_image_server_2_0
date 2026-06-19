"""
Модуль для подключения к базе данных PostgreSQL.

Этот модуль предоставляет функцию для создания подключения к БД,
используя переменные окружения из файла .env.
"""

import logging
import os

import psycopg
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

logger: logging.Logger = logging.getLogger(__name__)


def get_connection() -> psycopg.Connection:
    """
    Создаёт и возвращает подключение к базе данных PostgreSQL.

    Использует переменные окружения из файла .env:
        - DATABASE_NAME: имя базы данных
        - DATABASE_USER: имя пользователя
        - DATABASE_PASSWORD: пароль
        - DATABASE_HOST: хост (в Docker это имя сервиса 'db')
        - DATABASE_PORT: порт (в Docker это внутренний порт 5432)

    Returns:
        psycopg.Connection: Объект подключения к PostgreSQL.

    Raises:
        psycopg.Error: Если не удалось подключиться к БД.
    """
    try:
        conn: psycopg.Connection = psycopg.connect(
            dbname=os.getenv("DATABASE_NAME"),
            user=os.getenv("DATABASE_USER"),
            password=os.getenv("DATABASE_PASSWORD"),
            host=os.getenv("DATABASE_HOST"),
            port=int(os.getenv("DATABASE_PORT", "5432")),
        )
        logger.info("Successfully connected to PostgreSQL database.")
        return conn
    except Exception as e:
        logger.error("Failed to connect to PostgreSQL database: %s", e)
        raise