"""
Тестовый скрипт для проверки работы алгоритма детекции плагиата
Запуск: python Folder/manage.py shell < test_algorithm.py
Или в Django shell: exec(open('test_algorithm.py').read())
"""

import os
import tempfile
from django.core.files.base import ContentFile
from documents.models import Document, Status, Type
from documents.detectors import AdvancedPlagiarismDetector
from users.models import User

print("=" * 60)
print("ТЕСТИРОВАНИЕ АЛГОРИТМА ДЕТЕКЦИИ ПЛАГИАТА")
print("=" * 60)

# Получаем или создаём тестового пользователя
try:
    test_user = User.objects.get(username='test_user')
except User.DoesNotExist:
    test_user = User.objects.create_user(
        username='test_user',
        email='test@test.com',
        password='testpass123'
    )
    print(f"✓ Создан тестовый пользователь: {test_user.username}")

# Получаем или создаём другого пользователя для теста
try:
    test_user2 = User.objects.get(username='test_user2')
except User.DoesNotExist:
    test_user2 = User.objects.create_user(
        username='test_user2',
        email='test2@test.com',
        password='testpass123'
    )
    print(f"✓ Создан второй тестовый пользователь: {test_user2.username}")

# Получаем статус и тип по умолчанию
status = Status.objects.first()
doc_type = Type.objects.first()

if not status or not doc_type:
    print("✗ ОШИБКА: Нет статусов или типов в базе. Запустите миграции.")
    exit(1)

# Очищаем старые тестовые документы
Document.objects.filter(name__startswith='TEST_').delete()
print("✓ Очищены старые тестовые документы")

# Создаём тестовые текстовые файлы
test_text1 = """
Это первый тестовый документ для проверки алгоритма детекции плагиата.
Документ содержит уникальный текст, который не должен совпадать с другими.
Алгоритм должен показать высокую оригинальность для этого документа.
"""

test_text2 = """
Это второй тестовый документ с совершенно другим содержанием.
Текст этого документа не имеет ничего общего с первым документом.
Оригинальность должна быть высокой.
"""

test_text3 = """
Это первый тестовый документ для проверки алгоритма детекции плагиата.
Документ содержит уникальный текст, который не должен совпадать с другими.
Алгоритм должен показать высокую оригинальность для этого документа.
"""

# Создаём временные файлы
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
    f.write(test_text1)
    txt_file1_path = f.name

with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
    f.write(test_text2)
    txt_file2_path = f.name

with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
    f.write(test_text3)
    txt_file3_path = f.name

print("\n" + "=" * 60)
print("ТЕСТ 1: Создание документов с разным содержимым")
print("=" * 60)

# Создаём первый документ
doc1 = Document.objects.create(
    user=test_user,
    name='TEST_DOC1_unique',
    status=status,
    type=doc_type,
    processing_status='completed'
)
doc1.data.save('TEST_doc1_unique.docx', ContentFile(b'fake docx content'))
with open(txt_file1_path, 'rb') as f:
    doc1.txt_file.save('TEST_doc1_unique.txt', ContentFile(f.read()))
print(f"✓ Создан документ 1: {doc1.name} (ID: {doc1.id})")

# Создаём второй документ
doc2 = Document.objects.create(
    user=test_user2,
    name='TEST_DOC2_unique',
    status=status,
    type=doc_type,
    processing_status='completed'
)
doc2.data.save('TEST_doc2_unique.docx', ContentFile(b'fake docx content'))
with open(txt_file2_path, 'rb') as f:
    doc2.txt_file.save('TEST_doc2_unique.txt', ContentFile(f.read()))
print(f"✓ Создан документ 2: {doc2.name} (ID: {doc2.id})")

# Создаём третий документ (копия первого по тексту, но другое имя файла)
doc3 = Document.objects.create(
    user=test_user,
    name='TEST_DOC3_copy',
    status=status,
    type=doc_type,
    processing_status='completed'
)
doc3.data.save('TEST_doc3_copy.docx', ContentFile(b'fake docx content'))
with open(txt_file3_path, 'rb') as f:
    doc3.txt_file.save('TEST_doc3_copy.txt', ContentFile(f.read()))
print(f"✓ Создан документ 3: {doc3.name} (ID: {doc3.id}) - копия текста doc1")

print("\n" + "=" * 60)
print("ТЕСТ 2: Проверка без документов в общей базе (on_defense=False)")
print("=" * 60)

detector = AdvancedPlagiarismDetector()
result1 = detector.detect_plagiarism(doc1.id)
print(f"\nДокумент 1 ({doc1.name}):")
print(f"  Оригинальность: {result1['originality']}%")
print(f"  Сообщение: {result1['message']}")
print(f"  Статус: {result1['status']}")

print("\n" + "=" * 60)
print("ТЕСТ 3: Отправка doc2 на защиту и проверка doc1")
print("=" * 60)

doc2.on_defense = True
doc2.save()
print(f"✓ Документ 2 отправлен на защиту (on_defense=True)")

result1_after = detector.detect_plagiarism(doc1.id)
print(f"\nДокумент 1 ({doc1.name}) после отправки doc2 на защиту:")
print(f"  Оригинальность: {result1_after['originality']}%")
print(f"  Сообщение: {result1_after['message']}")
print(f"  Найдено похожих: {len(result1_after.get('similar_documents', []))}")

print("\n" + "=" * 60)
print("ТЕСТ 4: Проверка по имени файла - одинаковые имена")
print("=" * 60)

# Создаём документ с таким же именем файла, как у doc2
doc4 = Document.objects.create(
    user=test_user,
    name='TEST_DOC4_same_filename',
    status=status,
    type=doc_type,
    processing_status='completed'
)
doc4.data.save('TEST_doc2_unique.docx', ContentFile(b'fake docx content'))  # То же имя!
with open(txt_file2_path, 'rb') as f:
    doc4.txt_file.save('TEST_doc4_same_filename.txt', ContentFile(f.read()))
print(f"✓ Создан документ 4 с таким же именем файла, как у doc2")

result4 = detector.detect_plagiarism(doc4.id)
print(f"\nДокумент 4 ({doc4.name}) - должен показать 0% из-за совпадения имени файла:")
print(f"  Оригинальность: {result4['originality']}%")
print(f"  Сообщение: {result4['message']}")
print(f"  Найдено дубликатов по имени: {len(result4.get('source_matches', []))}")

print("\n" + "=" * 60)
print("ТЕСТ 5: Проверка doc3 (копия текста doc1) с doc1 на защите")
print("=" * 60)

doc1.on_defense = True
doc1.save()
print(f"✓ Документ 1 отправлен на защиту")

result3 = detector.detect_plagiarism(doc3.id)
print(f"\nДокумент 3 ({doc3.name}) - копия текста doc1:")
print(f"  Оригинальность: {result3['originality']}%")
print(f"  Сообщение: {result3['message']}")
print(f"  Найдено похожих: {len(result3.get('similar_documents', []))}")

print("\n" + "=" * 60)
print("ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
print("=" * 60)
print(f"Документ 1 (на защите): оригинальность = {result1_after.get('originality', 'N/A')}%")
print(f"Документ 2 (на защите): должен быть в общей базе")
print(f"Документ 3 (копия doc1): оригинальность = {result3.get('originality', 'N/A')}%")
print(f"Документ 4 (то же имя файла): оригинальность = {result4.get('originality', 'N/A')}%")

print("\n" + "=" * 60)
print("ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ:")
print("=" * 60)
print("1. Документ 1 без общей базы: 100% (нет документов для сравнения)")
print("2. Документ 1 после doc2 на защите: <100% (если тексты похожи)")
print("3. Документ 4 (то же имя файла): 0% (дубликат по имени)")
print("4. Документ 3 (копия doc1): <100% (низкая оригинальность из-за копии)")
print("=" * 60)

# Очистка временных файлов
os.unlink(txt_file1_path)
os.unlink(txt_file2_path)
os.unlink(txt_file3_path)

print("\n✓ Тестирование завершено!")

