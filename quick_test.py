"""
Быстрый тест алгоритма - запуск: python Folder/manage.py shell < quick_test.py
"""

from documents.models import Document
from documents.detectors import AdvancedPlagiarismDetector

print("=" * 60)
print("БЫСТРЫЙ ТЕСТ АЛГОРИТМА")
print("=" * 60)

# Получаем последние 2 документа
docs = Document.objects.all().order_by('-id')[:2]

if len(docs) < 2:
    print("✗ Нужно минимум 2 документа в базе для теста")
    exit(1)

doc1, doc2 = docs[0], docs[1]

print(f"\nДокумент 1: ID={doc1.id}, имя='{doc1.name}', on_defense={doc1.on_defense}, user={doc1.user_id}")
print(f"Документ 2: ID={doc2.id}, имя='{doc2.name}', on_defense={doc2.on_defense}, user={doc2.user_id}")

print("\n" + "=" * 60)
print("ТЕСТ 1: Проверка doc1")
print("=" * 60)

detector = AdvancedPlagiarismDetector()
result1 = detector.detect_plagiarism(doc1.id)

print(f"Оригинальность: {result1['originality']}%")
print(f"Статус: {result1['status']}")
print(f"Сообщение: {result1['message']}")
print(f"Найдено похожих документов: {len(result1.get('similar_documents', []))}")

if result1.get('source_matches'):
    print(f"Дубликаты по имени файла: {len(result1['source_matches'])}")

print("\n" + "=" * 60)
print("ТЕСТ 2: Проверка doc2")
print("=" * 60)

result2 = detector.detect_plagiarism(doc2.id)

print(f"Оригинальность: {result2['originality']}%")
print(f"Статус: {result2['status']}")
print(f"Сообщение: {result2['message']}")
print(f"Найдено похожих документов: {len(result2.get('similar_documents', []))}")

if result2.get('source_matches'):
    print(f"Дубликаты по имени файла: {len(result2['source_matches'])}")

print("\n" + "=" * 60)
print("АНАЛИЗ РЕЗУЛЬТАТОВ")
print("=" * 60)

# Проверяем имена файлов
if doc1.data and doc2.data:
    name1 = doc1.data.name.split('/')[-1] if '/' in doc1.data.name else doc1.data.name
    name2 = doc2.data.name.split('/')[-1] if '/' in doc2.data.name else doc2.data.name
    print(f"Имя файла doc1: {name1}")
    print(f"Имя файла doc2: {name2}")
    
    if name1 == name2:
        print("⚠ Имена файлов СОВПАДАЮТ - doc2 должен показать 0% если doc1 на защите")
    else:
        print("✓ Имена файлов РАЗНЫЕ")

# Проверяем статус защиты
print(f"\nДокументов на защите (on_defense=True): {Document.objects.filter(on_defense=True).count()}")
print(f"Документов НЕ на защите: {Document.objects.filter(on_defense=False).count()}")

print("\n" + "=" * 60)
print("ОЖИДАЕМОЕ ПОВЕДЕНИЕ:")
print("=" * 60)
print("1. Если имена файлов совпадают И doc1 на защите → doc2 должен показать 0%")
print("2. Если имена файлов разные → обычный анализ по тексту")
print("3. Сравнение только с документами on_defense=True")
print("4. Документы пользователя тоже сравниваются между собой")
print("=" * 60)

