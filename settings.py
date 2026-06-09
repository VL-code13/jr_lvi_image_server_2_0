from pathlib import Path
import os

# Базовый каталог проекта
BASE_DIR = Path(__file__).resolve().parent

# Получаем пути из переменных окружения или используем значения по умолчанию
IMAGES_DIR = Path(os.getenv('IMAGES_DIR', str(BASE_DIR / 'images')))
LOGS_DIR = Path(os.getenv('LOGS_DIR', str(BASE_DIR / 'logs')))

# Ограничения по размеру файлов
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 МБ
REQUEST_LIMIT = MAX_FILE_SIZE + 1024 * 1024  # Лимит запроса с запасом

# Поддерживаемые форматы изображений и их расширения
ALLOWED_IMAGE_FORMATS = {
    'JPEG': 'jpg',
    'PNG': 'png',
    'GIF': 'gif'
}


def ensure_directories_exist():
    """Создаёт необходимые директории, если их нет, с обработкой ошибок."""
    for directory in [IMAGES_DIR, LOGS_DIR]:
        try:
            # Создаём директорию с родительскими папками, если нужно
            directory.mkdir(exist_ok=True, parents=True)
            # Проверяем, что директория действительно существует
            if not directory.exists():
                raise RuntimeError(f"Failed to create directory: {directory}")

            # Пытаемся установить права доступа (755: rwxr-xr-x)не падаем, если не удалось изменить права (например, в Docker)
            try:
                os.chmod(directory, 0o755)
            except PermissionError:
                print(f"Warning: Could not change permissions for {directory} (running in Docker?)")

            print(f"Directory created/verified: {directory}")
        except PermissionError as e:
            print(f"Permission denied when creating {directory}: {e}")
            raise
        except Exception as e:
            print(f"Error creating directory {directory}: {e}")
            raise

