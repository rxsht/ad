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