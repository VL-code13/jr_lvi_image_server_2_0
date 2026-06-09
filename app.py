import traceback

from flask import Flask, render_template, jsonify, request, url_for, send_from_directory
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import RequestEntityTooLarge, BadRequest
import logging
import uuid
from io import BytesIO
from flask_cors import CORS

from database.models import create_images
from database.repository import save_metadata
# Импортируем настройки из отдельного файла
from settings import (
    BASE_DIR,
    IMAGES_DIR,
    LOGS_DIR,
    MAX_FILE_SIZE,
    REQUEST_LIMIT,
    ALLOWED_IMAGE_FORMATS,
    ensure_directories_exist
)

app = Flask(__name__)
CORS(app)

# Применяем настройки
app.config['MAX_CONTENT_LENGTH'] = REQUEST_LIMIT

# Создаём директории при запуске приложения
ensure_directories_exist()

# Настройка логирования
logging.basicConfig(
    filename=LOGS_DIR / 'app.log',
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)


def detect_image_extension(file_data: bytes) -> str | None:
    """Определяет расширение изображения по его содержимому."""
    try:
        with Image.open(BytesIO(file_data)) as image:
            image.verify()
            return ALLOWED_IMAGE_FORMATS.get(image.format)
    except (UnidentifiedImageError, OSError, ValueError):
        return None


@app.get('/')
def home():
    """Главная страница сервиса."""
    return render_template('index.html')


@app.get('/upload')
def upload_page():
    """Страница загрузки изображений."""
    return render_template('upload.html')


@app.get('/images/')
def images_page():
    """Страница с каталогом загруженных изображений.
      Примечание: сами файлы отдаются через Nginx,
    но список файлов формирует Flask для отображения в шаблоне.
    """
    images = []
    try:
        for image_path in sorted(IMAGES_DIR.iterdir(), key=lambda path: path.stat().st_mtime, reverse=True):
            if not image_path.is_file():
                continue
            # Формируем URL, который будет обрабатываться Nginx
            relative_url: str = url_for('get_image', filename=image_path.name)
            full_url = request.host_url.rstrip('/') + relative_url
            images.append({
                'name': image_path.name,
                'url': relative_url,
                'full_url': full_url,
                'size': image_path.stat().st_size
            })
    except Exception as e:
        logger.error(f'Error reading images directory: {e}')
        return jsonify({'error': 'Failed to read images directory'}), 500
    return render_template('images.html', images=images)


@app.post('/upload')
def upload_image():
    """Обработчик загрузки изображений."""
    uploaded_file = request.files.get('image')
    if uploaded_file is None:
        logger.warning('No image uploaded. Файл image не найден в запросе.')
        return jsonify({
            'error': 'No image uploaded. Файл не найден. Поле формы должно называться image'
        }), 400
    # Проверяем расширение файла
    original_filename = uploaded_file.filename or 'Unknown'

    # Проверяем, что файл имеет имя
    if not original_filename or original_filename == 'Unknown':
        logger.warning('File has no name')
        return jsonify({'error': 'Файл не имеет имени'}), 400

    try:
        file_data = uploaded_file.read()  # Читаем данные файла
    except Exception as e:
        logger.error(f'Error reading file {original_filename}: {e}')
        return jsonify({'error': 'Error reading file'}), 500

    if not file_data:
        logger.warning(f'Empty file uploaded: {original_filename}')
        return jsonify({'error': 'Файл пустой'}), 400

    if len(file_data) > MAX_FILE_SIZE:
        logger.warning(f'File {original_filename} exceeds size limit (5 MB)')
        return jsonify({'error': 'Файл не должен быть больше 5 МБ.'}), 413

    image_extension = detect_image_extension(file_data)
    if image_extension is None:
        logger.warning(f'Unsupported image format: {original_filename}')
        return jsonify({
            'error': 'Файл неверного формата. Поддерживаются только jpg, png, gif.'
        }), 400

    # Генерируем уникальное имя файла
    unique_filename = f'{uuid.uuid4().hex}.{image_extension}'  
    target_path = IMAGES_DIR / unique_filename

    #Сначала сохраняем файл на диск, потом в БД
    try:
        target_path.write_bytes(file_data)
        logger.info(f'File saved to disk: {unique_filename}')
    except PermissionError as e:
        logger.error(f'Permission denied when saving file {unique_filename}: {e}')
        return jsonify({'error': 'Нет прав на запись файла'}), 500
    except OSError as e:
        logger.error(f'OS error when saving file {unique_filename}: {e}')
        return jsonify({'error': 'Ошибка файловой системы'}), 500

    # Сохраняем метаданные в БД
    try:
        save_metadata(
            filename=unique_filename,
            original_name=original_filename,
            size=len(file_data),
            file_type=image_extension
        )
    except Exception as e:
        # Если БД упала, удаляем файл с диска
        target_path.unlink(missing_ok=True)
        logger.error(f'File deleted. Error saving metadata file {unique_filename} to DB: {e}')
        return jsonify({'error': 'Error saving metadata file'}), 500
    # Создаём директорию, если её нет
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Сохраняем файл с обработкой ошибок
    try:
        target_path.write_bytes(file_data)
        logger.info(f'Image uploaded successfully: {original_filename} → {unique_filename}')
    except PermissionError as e:
        logger.error(f'Permission denied when saving file {unique_filename}: {e}')
        return jsonify({'error': 'Нет прав на запись файла'}), 500
    except OSError as e:
        logger.error(f'OS error when saving file {unique_filename}: {e}')
        return jsonify({'error': 'Ошибка файловой системы'}), 500
    except Exception as e:
        logger.error(f'Unexpected error when saving file {unique_filename}: {e}')
        return jsonify({'error': 'Неизвестная ошибка при сохранении файла'}), 500

    # Формируем URL для доступа к изображению (через Nginx)
    relative_url = url_for('get_image', filename=unique_filename)  # f'/images/{unique_filename}'
    full_url = request.host_url.rstrip('/') + relative_url

    return jsonify({
        'message': 'Изображение успешно загружено ',
        'id': unique_filename,
        'original_name': original_filename,
        'url': relative_url,
        'full_url': full_url,
        'size': len(file_data)
    }), 201


@app.get('/images/<path:filename>')
def get_image(filename: str):
    """Отдаёт запрошенное изображение."""
    file_path = IMAGES_DIR / filename
    if not file_path.exists():
        logger.warning(f'Requested file not found: {filename}')
        return jsonify({'error': 'File not found'}), 404
    if not file_path.is_file():
        logger.warning(f'Invalid file path requested: {filename}')
        return jsonify({'error': 'Invalid file path'}), 400
    try:
        return send_from_directory(IMAGES_DIR, filename)
    except Exception as e:
        logger.error(f'Error serving file {filename}: {e}')
        return jsonify({'error': 'Error serving file'}), 500


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    """Обрабатывает ошибку превышения размера файла."""
    logger.error('File too large: %s', e)
    return jsonify({'error': 'Файл слишком большой'}), 413


@app.errorhandler(BadRequest)
def handle_bad_request(e):
    """Обрабатывает некорректные запросы."""
    logger.error('Bad request: %s', e)
    return jsonify({'error': 'Некорректный запрос'}), 400


# Создаём таблицы при запуске приложения
def init_db():
    """Инициализация базы данных."""
    try:
        result = create_images()
        logger.info(result)
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


if __name__ == '__main__':
    # Создаём необходимые директории
    ensure_directories_exist()

    # Инициализируем БД
    init_db()

    # Запускаем приложение
    app.run(host='0.0.0.0', port=3000, debug=True)# Отключаем debug в продакшене
