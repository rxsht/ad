import re
import numpy as np
import os
import logging

logger = logging.getLogger(__name__)

# Глобальная переменная для хранения модели (ленивая загрузка)
_model = None
MODEL_NAME = 'paraphrase-MiniLM-L6-v2'


def get_model():
    """
    Получает модель SentenceTransformer с ленивой загрузкой.
    Загружает модель только при первом вызове.
    Использует кеш HuggingFace из переменных окружения или volume в Docker.
    """
    global _model
    
    if _model is None:
        try:
            # Устанавливаем пути к кешу HuggingFace из переменных окружения
            # В Docker это будет /root/.cache/huggingface (настроено через volume hf_cache)
            hf_home = os.environ.get('HF_HOME', os.environ.get('TRANSFORMERS_CACHE', '/root/.cache/huggingface'))
            cache_dir = os.path.join(hf_home, 'hub')
            os.makedirs(cache_dir, exist_ok=True)
            
            logger.info(f"Загрузка модели {MODEL_NAME} из кеша {hf_home}...")
            from sentence_transformers import SentenceTransformer
            # Модель автоматически использует кеш из переменных окружения
            _model = SentenceTransformer(MODEL_NAME, cache_folder=hf_home)
            logger.info(f"Модель {MODEL_NAME} успешно загружена (размер: ~80MB)")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Ошибка при загрузке модели {MODEL_NAME}: {error_msg}")
            
            # Предупреждение, если модель не найдена в кеше
            if "not found" in error_msg.lower() or "404" in error_msg:
                logger.warning(f"Модель {MODEL_NAME} не найдена в кеше. При первом запуске она будет скачана из интернета.")
            
            raise RuntimeError(f"Не удалось загрузить модель векторизации {MODEL_NAME}: {error_msg}")
    
    return _model


def extract_chapters_from_txt(txt_filename):
    """
    Извлекает главы из текста в txt файле, разделяя по пустой строке.
    Каждая глава в итоге будет словарем с ключом "название главы" и значением "содержание".
    """
    with open(txt_filename, 'r', encoding='utf-8') as file:
        text = file.read()

    # Разделяем текст на главы по пустым строкам
    chapters = text.split('\n\n')  # Пустая строка разделяет главы
    chapters_dict = {}
    start_index = 1 if len(chapters) % 2 != 0 else 0

    for i in range(start_index, len(chapters), 2):
        if i + 1 < len(chapters):
            title = chapters[i].strip()
            content = chapters[i + 1].strip()

            if title:
                chapters_dict[title] = content

    if len(chapters_dict) == 0:
        chapters_dict["Бгуир"] = text

    return chapters_dict

def split_text_to_sentences(block):
    """
    Разбивает блок текста на предложения.
    """
    # Разбиваем текст на предложения по точкам
    sentences = re.split(r'(?<=\.)\s+', block)

    return sentences

def process_text(txt_filename):
    """
    Генерирует вектор документа, усредняя векторы предложений и блоков.
    """
    # Разделяем текст на главы
    chapters = extract_chapters_from_txt(txt_filename)

    # Генерация векторов для каждого блока
    all_chapter_vectors = []
    for chapter_title, chapter_content in chapters.items():

        sentences = split_text_to_sentences(chapter_content + chapter_title)

        # Фильтруем пустые предложения
        sentences = [sentence.strip() for sentence in sentences if sentence.strip()]

        if sentences:  # Только если есть предложения
            try:
                # Получаем модель (ленивая загрузка)
                model = get_model()
                # Генерация векторов для каждого предложения
                sentence_vectors = [model.encode(sentence) for sentence in sentences]

                chapter_vector = np.mean(sentence_vectors, axis=0)
                all_chapter_vectors.append(chapter_vector)
            except Exception as e:
                logger.error(f"Ошибка при векторизации предложений: {e}")
                # Продолжаем обработку, даже если векторизация не удалась
                # Это позволит обработать остальные главы
                pass

    # Усредняем векторы для всех глав, чтобы получить финальный вектор документа
    if all_chapter_vectors:
        document_vector = np.mean(all_chapter_vectors, axis=0)
        return document_vector  # Возвращаем numpy array
    else:
        return None  # Если нет векторов, возвращаем None

# # Пример использования
# txt_filename = 'output.txt'  # Укажите путь к вашему текстовому файлу
# document_vector = process_text(txt_filename)
# print(f"Вектор документа: {document_vector}")
