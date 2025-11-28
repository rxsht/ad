import hashlib

def generate_hashed_shingles(text, shingle_size=5):
    """
    Создаёт хэшированные шинглы для текста.
    """
    tokens = text.split()
    shingles = [' '.join(tokens[i:i + shingle_size]) for i in range(len(tokens) - shingle_size + 1)]
    hashed_shingles = {hashlib.md5(shingle.encode('utf-8')).hexdigest() for shingle in shingles}
    return hashed_shingles

def coef_similarity_hashed(shingles1, shingles2):
    """
    Рассчитывает коэффициент схожести для двух наборов хэшированных шинглов.
    """
    intersection = len(shingles1 & shingles2)
    union = len(shingles1 | shingles2)  # Исправлено: теперь используется объединение множеств
    return intersection / union if union > 0 else 0

def calculate_originality_large_texts(user_doc, similar_docs, shingle_size=5):
    """
    Рассчитывает процент оригинальности для большого текста.
    Пример использования:
    print(f"Процент оригинальности: {originality:.2f}%")
    """
    user_shingles = generate_hashed_shingles(user_doc, shingle_size)

    all_db_shingles = set()

    for doc in similar_docs:
        db_shingles = generate_hashed_shingles(doc, shingle_size)
        all_db_shingles.update(db_shingles)
    
    similarity = coef_similarity_hashed(user_shingles, all_db_shingles)

    originality = 100 - (similarity * 100) - 0.01

    return originality

def calculate_similarity_by_source(user_doc, similar_doc, shingle_size=5):
    """
    Рассчитывает процент совпадений между проверяемым документом и одним источником.
    Возвращает процент совпадений (0-100).
    
    Args:
        user_doc: Текст проверяемого документа
        similar_doc: Текст источника для сравнения
        shingle_size: Размер шинглов (по умолчанию 5)
    
    Returns:
        float: Процент совпадений от 0 до 100
    """
    if not user_doc or not similar_doc:
        return 0.0
    
    if not isinstance(user_doc, str) or not isinstance(similar_doc, str):
        return 0.0
    
    user_shingles = generate_hashed_shingles(user_doc, shingle_size)
    source_shingles = generate_hashed_shingles(similar_doc, shingle_size)
    
    if not user_shingles or not source_shingles:
        return 0.0
    
    similarity = coef_similarity_hashed(user_shingles, source_shingles)
    similarity_percent = similarity * 100
    
    return max(0.0, min(100.0, similarity_percent))  # Ограничиваем от 0 до 100

def detect_citations(user_doc, similar_doc, shingle_size=3):
    """
    Определяет процент цитирований (короткие совпадения, которые могут быть цитатами).
    Использует меньший размер шинглов для выявления коротких совпадений.
    
    Цитирования рассчитываются как процент совпавших коротких шинглов от общего 
    количества шинглов проверяемого документа. Это позволяет выявить точные 
    совпадения коротких фрагментов текста.
    
    Args:
        user_doc: Текст проверяемого документа
        similar_doc: Текст источника для сравнения
        shingle_size: Размер шинглов для цитирований (по умолчанию 3, меньше чем для общих совпадений)
    
    Returns:
        float: Процент цитирований от 0 до 100
    """
    if not user_doc or not similar_doc:
        return 0.0
    
    if not isinstance(user_doc, str) or not isinstance(similar_doc, str):
        return 0.0
    
    user_shingles = generate_hashed_shingles(user_doc, shingle_size)
    source_shingles = generate_hashed_shingles(similar_doc, shingle_size)
    
    if not user_shingles:
        return 0.0
    
    # Находим короткие совпадения (потенциальные цитаты)
    short_matches = user_shingles & source_shingles
    
    # Рассчитываем процент цитирований относительно общего объема текста проверяемого документа
    # Это показывает, какая доля текста пользователя совпадает с источником
    citation_percent = (len(short_matches) / len(user_shingles)) * 100
    
    return max(0.0, min(100.0, citation_percent))  # Ограничиваем от 0 до 100

# Пример использования
# 
# user_document = """
#     А и И сидели на трубе А упало Б пропало кто остался на трубе
#     """
# similar_documents = ["""
# трубе
# """
# ]
# originality = calculate_originality_large_texts(user_document, similar_documents, shingle_size=1)
# print(f"Процент оригинальности: {originality:.2f}%")