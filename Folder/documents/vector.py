import re
import numpy as np
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('paraphrase-MiniLM-L6-v2')


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

def process_text(text_content):
    """
    Генерирует вектор документа, усредняя векторы предложений и блоков.
    """
    # Разделяем текст на главы
    chapters = extract_chapters_from_txt(text_content)

    # Генерация векторов для каждого блока
    all_chapter_vectors = []
    for chapter_title, chapter_content in chapters.items():
      
        sentences = split_text_to_sentences(chapter_content+chapter_title)
        
        # Генерация векторов для каждого предложения
        sentence_vectors = [model.encode(sentence) for sentence in sentences]
        
        
        chapter_vector = np.mean(sentence_vectors, axis=0)
        all_chapter_vectors.append(chapter_vector)
    
    # Усредняем векторы для всех глав, чтобы получить финальный вектор документа
    document_vector = np.mean(all_chapter_vectors, axis=0)
    return document_vector.tolist()  # Возвращаем вектор документа в виде списка

# # Пример использования
# txt_filename = 'output.txt'  # Укажите путь к вашему текстовому файлу
# document_vector = process_text(txt_filename)
# print(f"Вектор документа: {document_vector}")
