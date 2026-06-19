"""
Основной модуль Flask-приложения «Сервер картинок 2.0».

Предоставляет REST API и веб-интерфейс для:
- загрузки изображений (JPG, PNG, GIF);
- просмотра списка загруженных изображений с пагинацией;
- удаления изображений;
- резервного копирования базы данных.
"""
import traceback
import os
import math
from email import message

from PIL.ImageChops import offset
from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_from_directory,
    url_for,
    redirect,
)
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge
import logging
import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional
from database.models import create_images
from database.repository import (
    delete_image_by_id,
    get_image_by_id,
    get_images_list,
    get_total_images_count,
    save_metadata,
)
from settings import (
    BASE_DIR,
    ALLOWED_IMAGE_FORMATS,
    IMAGES_DIR,
    LOGS_DIR,
    MAX_FILE_SIZE,
    REQUEST_LIMIT,
    ensure_directories_exist,
)

app = Flask(__name__)
CORS(app)

# Применяем настройки
app.config['MAX_CONTENT_LENGTH'] = REQUEST_LIMIT

# Создаём директории при запуске приложения
ensure_directories_exist()

# ──────────────────────────────────────────────
# Настройка логирования
# ──────────────────────────────────────────────
logging.basicConfig(
    filename=LOGS_DIR / "app.log",
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8",
)

logger: logging.Logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────
def detect_image_extension(file_data: bytes) -> Optional[str]:
    """
    Определяет расширение изображения по его бинарному содержимому.

    Args:
        file_data: Бинарные данные файла.

    Returns:
        Строка с расширением (``'jpg'``, ``'png'``, ``'gif'``)
        или ``None``, если формат не поддерживается.
    """
    try:
        with Image.open(BytesIO(file_data)) as image:
            fmt: Optional[str] = image.format
            image.verify()
        return ALLOWED_IMAGE_FORMATS.get(fmt)
    except (UnidentifiedImageError, OSError, ValueError):
        return None

# ──────────────────────────────────────────────
# Маршруты: страницы
# ──────────────────────────────────────────────
@app.get("/")
def home() -> str:
    """Главная страница сервиса."""
    return render_template("index.html")


@app.get("/upload")
def upload_page() -> str:
    """Страница загрузки изображений."""
    return render_template("upload.html")


@app.get("/images-list")
def images_page() -> str:
    """
    Страница списка загруженных изображений с пагинацией.

    Query-параметры:
        page (int): Номер страницы (по умолчанию 1).

    Returns:
        Отрендеренный HTML-шаблон ``images_list.html``.
    """
    page: int = request.args.get("page", 1, type=int)
    per_page: int = 10
    offset = (page -1) * per_page

    try:
        total_images: int = get_total_images_count()
        total_pages: int = math.ceil(total_images / per_page) if total_images > 0 else 1
        images = get_images_list(per_page, offset)

        formated_images = []
        for img in images:
            img_id, filename, original_filename, size, upload_time,file_type = img
            formated_images.append({
                'id': img_id,
                'filename': filename,
                'original_filename': original_filename,
                'size_kb': round(size / 1024, 2),
                'upload_time': upload_time.strftime('%Y-%m-%d %H:%M:%S'),
                'file_type': file_type,
                'url':f'/images/{filename}'
            })
        return render_template(
            'images.html',
            images=formated_images,
            page=page,
            total_pages=total_pages,
            has_prev=page > 1,
            has_next=page < total_pages
        )
    except Exception as e:
        logger.error(f'Error reading images from database: {e}')
        return jsonify({'error': 'Failed to read images list'}), 500


'''
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


'''

'''
@app.get('/images/')
def images_page():
    """Страница с каталогом загруженных изображений и пагинацией."""
    page: int = request.args.get("page", 1, type=int)
    per_page: int = 12  # Можно настроить под дизайн

    if page < 1:
        page = 1

    try:
        # Получаем все файлы
        all_images = sorted(
            IMAGES_DIR.iterdir(),
            key=lambda path: path.stat().st_mtime,
            reverse=True
        )
        total = len(all_images)

        total_pages: int = max(1, (total + per_page - 1) // per_page)

        if page > total_pages and total > 0:
            page = total_pages

        offset: int = (page - 1) * per_page
        paginated_images = all_images[offset:offset + per_page]

        images = []
        for image_path in paginated_images:
            if not image_path.is_file():
                continue
            relative_url: str = url_for('get_image', filename=image_path.name)
            full_url = request.host_url.rstrip('/') + relative_url
            images.append({
                'name': image_path.name,
                'url': relative_url,
                'full_url': full_url,
                'size': image_path.stat().st_size,
                'modified': image_path.stat().st_mtime
            })

    except Exception as e:
        logger.error(f'Error reading images directory: {e}')
        return jsonify({'error': 'Failed to read images directory'}), 500

    return render_template(
        'images.html',
        images=images,
        page=page,
        total_pages=total_pages,
        total=total
    )

'''
# ──────────────────────────────────────────────
# Маршруты: API загрузки
# ──────────────────────────────────────────────
@app.post("/upload")
def upload_image():
    """
    Обработчик загрузки изображений.

    Принимает файл из поля формы ``image``, проверяет формат и размер,
    сохраняет на диск и записывает метаданные в PostgreSQL.

    Returns:
        JSON с информацией о загруженном файле (статус 201)
        или JSON с описанием ошибки.
    """
    uploaded_file = request.files.get("image")
    if uploaded_file is None:
        logger.warning("No image uploaded. Файл image не найден в запросе.")
        return jsonify({
            "error": "No image uploaded. Файл не найден. Поле формы должно называться image",
        }), 400

    original_filename: str = uploaded_file.filename or "Unknown"

    if not original_filename or original_filename == "Unknown":
        logger.warning("File has no name")
        return jsonify({"error": "Файл не имеет имени"}), 400

    try:
        file_data: bytes = uploaded_file.read()
    except Exception as e:
        logger.error(f"Error reading file {original_filename}: {e}")
        return jsonify({"error": "Error reading file"}), 500

    if not file_data:
        logger.warning(f"Empty file uploaded: {original_filename}")
        return jsonify({"error": "Файл пустой"}), 400

    if len(file_data) > MAX_FILE_SIZE:
        logger.warning(f"File {original_filename} exceeds size limit (5 MB)")
        return jsonify({"error": "Файл не должен быть больше 5 МБ."}), 413

    image_extension: Optional[str] = detect_image_extension(file_data)
    if image_extension is None:
        logger.warning(f"Unsupported image format: {original_filename}")
        return jsonify({
            "error": "Файл неверного формата. Поддерживаются только jpg, png, gif.",
        }), 400

    # Генерируем уникальное имя файла
    unique_filename: str = f"{uuid.uuid4().hex}.{image_extension}"
    target_path: Path = IMAGES_DIR / unique_filename
    target_path.parent.mkdir(parents=True, exist_ok=True)
    # Сохраняем файл на диск
    try:
        target_path.write_bytes(file_data)
        logger.info(f"File saved to disk: {unique_filename}")
    except PermissionError as e:
        logger.error(f"Permission denied when saving file {unique_filename}: {e}")
        return jsonify({"error": "Нет прав на запись файла"}), 500
    except OSError as e:
        logger.error(f"OS error when saving file {unique_filename}: {e}")
        return jsonify({"error": "Ошибка файловой системы"}), 500
    # Сохраняем метаданные в БД
    try:
        save_metadata(
            filename=unique_filename,
            original_filename=original_filename,
            size=len(file_data),
            file_type=image_extension,
        )
    except Exception as e:
        target_path.unlink(missing_ok=True) # Если БД упала — удаляем файл с диска (откат)
        logger.error(f"File deleted. Error saving metadata for {unique_filename} to DB: {e}")
        return jsonify({"error": "Error saving metadata file"}), 500
    return jsonify({
        'message':'Изображение успешно загружено',
        'filename': unique_filename,
        'original_filename': original_filename,
        'url': f'/images/{unique_filename}',
        'full_url': request.host_url.rstrip('/') + f'/images/{unique_filename}',
        'size': len(file_data)
    }), 201
    logger.info(f"Image uploaded successfully: {original_filename} → {unique_filename}")

# ──────────────────────────────────────────────
# Маршруты: удаление
# ──────────────────────────────────────────────
@app.get("/delete/<int:id>")
def delete_image(id: int):
    """
    Удаляет изображение из базы данных и с диска.

    Args:
        id: Уникальный идентификатор записи в таблице ``images``.

    Returns:
        JSON с результатом операции или JSON с ошибкой.
    """
    try:
        image: Optional[dict] = get_image_by_id(id)
        if image is None:
            logger.warning(f"Image with id={id} not found in database")
            return jsonify({"error": "Изображение не найдено"}), 404

        img_id, filename = image
        delete_image_by_id(id)

        # Удаляем физический файл
        file_path: Path = IMAGES_DIR / filename
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Physical file deleted: {filename} from disk")
        return redirect(url_for('image_page')

    except Exception as e:
        logger.error(f"Error deleting physical file {filename}: {e}"))

        # Удаляем запись из БД
        delete_image_by_id(image_id)
        logger.info(f"Image record deleted from DB: id={image_id}, file={filename}")

# ──────────────────────────────────────────────
# Маршруты: отдача файлов (Nginx fallback)
# ──────────────────────────────────────────────
@app.get("/images/<path:filename>")
def get_image(filename: str):
    """
    Отдаёт запрошенное изображение.

    Args:
        filename: Имя файла изображения.

    Returns:
        Файл изображения или JSON с ошибкой.
    """
    file_path: Path = IMAGES_DIR / filename
    if not file_path.exists():
        logger.warning(f"Requested file not found: {filename}")
        return jsonify({"error": "File not found"}), 404
    if not file_path.is_file():
        logger.warning(f"Invalid file path requested: {filename}")
        return jsonify({"error": "Invalid file path"}), 400
    try:
        return send_from_directory(str(IMAGES_DIR), filename)
    except Exception as e:
        logger.error(f"Error serving file {filename}: {e}")
        return jsonify({"error": "Error serving file"}), 500


# ──────────────────────────────────────────────
# Обработчики ошибок
# ──────────────────────────────────────────────
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e: RequestEntityTooLarge):
    """Обрабатывает ошибку превышения размера файла."""
    logger.error("File too large: %s", e)
    return jsonify({"error": "Файл слишком большой"}), 413


@app.errorhandler(BadRequest)
def handle_bad_request(e: BadRequest):
    """Обрабатывает некорректные запросы."""
    logger.error("Bad request: %s", e)
    return jsonify({"error": "Некорректный запрос"}), 400


if __name__ == "__main__":
    ensure_directories_exist()
    create_images()
    app.run(host="0.0.0.0", port=3000, debug=True)

'''
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
            original_filename=original_filename,
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
        'original_filename': original_filename,
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
'''