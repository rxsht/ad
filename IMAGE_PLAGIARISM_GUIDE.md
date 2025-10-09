# 📸 РУКОВОДСТВО: Добавление проверки изображений на плагиат

## 🎯 ЗАДАЧА
Добавить в систему проверку изображений из документов (PDF/DOCX) на плагиат, чтобы обнаруживать скопированные схемы, графики, скриншоты в курсовых работах.

---

## 📋 ПОЛНЫЙ ПЛАН РЕАЛИЗАЦИИ

### ЭТАП 1: Подготовка инфраструктуры (30 мин)

#### 1.1 Добавить зависимости

**Обновить `requirements.txt`:**
```python
# Обработка изображений
Pillow==10.2.0              # Работа с изображениями
opencv-python==4.9.0.80     # Компьютерное зрение
imagehash==4.3.1            # Перцептуальные хэши
PyMuPDF==1.23.0             # Извлечение изображений из PDF (fitz)
```

**Установка:**
```bash
pip install Pillow opencv-python imagehash PyMuPDF
```

---

#### 1.2 Создать модель для хранения изображений

**Создать файл `Folder/documents/image_models.py`:**
```python
from django.db import models
from pgvector.django import VectorField

class DocumentImage(models.Model):
    """Изображение извлечённое из документа"""
    document = models.ForeignKey('Document', on_delete=models.CASCADE, related_name='images')
    page_number = models.IntegerField(verbose_name='Номер страницы')
    image_index = models.IntegerField(verbose_name='Индекс на странице')
    
    # Файл изображения
    image_file = models.ImageField(upload_to='extracted_images/', blank=True, null=True)
    
    # Метаданные
    width = models.IntegerField()
    height = models.IntegerField()
    format = models.CharField(max_length=10)
    size_bytes = models.IntegerField()
    
    # Перцептуальные хэши для быстрого поиска
    phash = models.BigIntegerField(null=True, verbose_name='Perceptual hash')
    dhash = models.BigIntegerField(null=True, verbose_name='Difference hash')
    ahash = models.BigIntegerField(null=True, verbose_name='Average hash')
    
    # CLIP эмбеддинг для семантического поиска
    embedding = VectorField(dimensions=512, null=True, blank=True)
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'document_images'
        indexes = [
            models.Index(fields=['phash']),
            models.Index(fields=['document', 'page_number']),
        ]
        verbose_name = 'Изображение документа'
        verbose_name_plural = 'Изображения документов'


class ImageSimilarity(models.Model):
    """Схожесть между изображениями"""
    image1 = models.ForeignKey(DocumentImage, on_delete=models.CASCADE, related_name='similarities_as_img1')
    image2 = models.ForeignKey(DocumentImage, on_delete=models.CASCADE, related_name='similarities_as_img2')
    
    # Метрики схожести
    phash_distance = models.IntegerField(verbose_name='Hamming distance pHash')
    cosine_similarity = models.FloatField(verbose_name='Косинусное сходство CLIP')
    ssim_score = models.FloatField(null=True, verbose_name='SSIM структурное сходство')
    
    # Общая оценка
    is_duplicate = models.BooleanField(default=False)
    confidence = models.FloatField(default=0.0, verbose_name='Уверенность 0-1')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'image_similarities'
        unique_together = [('image1', 'image2')]
        indexes = [
            models.Index(fields=['is_duplicate']),
            models.Index(fields=['-confidence']),
        ]
```

**Создать миграцию:**
```bash
python Folder/manage.py makemigrations
python Folder/manage.py migrate
```

Также нужно **включить pgvector расширение** если ещё не:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Для текстового поиска
```

---

### ЭТАП 2: Извлечение изображений (45 мин)

#### 2.1 Создать экстрактор изображений

**Файл `Folder/documents/image_extractor.py`:**
```python
"""
Извлечение изображений из PDF и DOCX
"""

import os
import io
from PIL import Image
import fitz  # PyMuPDF
from docx import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph


class ImageExtractor:
    """Класс для извлечения изображений"""
    
    def __init__(self, min_width=100, min_height=100):
        """
        Args:
            min_width: минимальная ширина изображения
            min_height: минимальная высота изображения
        """
        self.min_width = min_width
        self.min_height = min_height
    
    def extract_from_pdf(self, pdf_path, output_dir):
        """
        Извлекает изображения из PDF
        
        Returns:
            List[dict]: список извлечённых изображений с метаданными
        """
        images = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images()
                
                for img_index, img_info in enumerate(image_list):
                    xref = img_info[0]
                    
                    # Извлекаем изображение
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # Открываем через PIL
                    image = Image.open(io.BytesIO(image_bytes))
                    
                    # Фильтруем маленькие изображения (иконки, пиксели)
                    if image.width < self.min_width or image.height < self.min_height:
                        continue
                    
                    # Конвертируем в RGB если нужно
                    if image.mode not in ('RGB', 'L'):
                        image = image.convert('RGB')
                    
                    # Сохраняем
                    filename = f'page_{page_num+1}_img_{img_index+1}.png'
                    filepath = os.path.join(output_dir, filename)
                    image.save(filepath, 'PNG')
                    
                    images.append({
                        'page': page_num + 1,
                        'index': img_index + 1,
                        'path': filepath,
                        'width': image.width,
                        'height': image.height,
                        'format': image.format or 'PNG',
                        'size': len(image_bytes)
                    })
            
            doc.close()
            
        except Exception as e:
            raise Exception(f"Ошибка извлечения изображений из PDF: {e}")
        
        return images
    
    def extract_from_docx(self, docx_path, output_dir):
        """
        Извлекает изображения из DOCX
        
        Returns:
            List[dict]: список извлечённых изображений
        """
        images = []
        
        try:
            doc = DocxDocument(docx_path)
            
            # Извлекаем изображения из relationships
            for rel_id, rel in doc.part.rels.items():
                if "image" in rel.target_ref:
                    try:
                        image_bytes = rel.target_part.blob
                        image = Image.open(io.BytesIO(image_bytes))
                        
                        # Фильтруем маленькие
                        if image.width < self.min_width or image.height < self.min_height:
                            continue
                        
                        # Конвертируем
                        if image.mode not in ('RGB', 'L'):
                            image = image.convert('RGB')
                        
                        # Сохраняем
                        filename = f'image_{len(images)+1}.png'
                        filepath = os.path.join(output_dir, filename)
                        image.save(filepath, 'PNG')
                        
                        images.append({
                            'page': 0,  # DOCX не имеет страниц
                            'index': len(images) + 1,
                            'path': filepath,
                            'width': image.width,
                            'height': image.height,
                            'format': image.format or 'PNG',
                            'size': len(image_bytes)
                        })
                        
                    except Exception:
                        continue
        
        except Exception as e:
            raise Exception(f"Ошибка извлечения изображений из DOCX: {e}")
        
        return images
    
    def extract(self, file_path, output_dir):
        """
        Универсальный метод извлечения
        
        Args:
            file_path: путь к файлу
            output_dir: директория для сохранения
        """
        os.makedirs(output_dir, exist_ok=True)
        
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            return self.extract_from_pdf(file_path, output_dir)
        elif ext == '.docx':
            return self.extract_from_docx(file_path, output_dir)
        else:
            raise ValueError(f"Неподдерживаемый формат: {ext}")
```

---

### ЭТАП 3: Вычисление хэшей и эмбеддингов (60 мин)

#### 3.1 Создать процессор изображений

**Файл `Folder/documents/image_processor.py`:**
```python
"""
Обработка изображений: хэширование и векторизация
"""

import imagehash
from PIL import Image
import numpy as np
import cv2
from skimage.metrics import structural_similarity as ssim


class ImageProcessor:
    """Обработка и сравнение изображений"""
    
    def __init__(self):
        self.hash_size = 8  # Размер хэша (8x8 = 64 бита)
    
    def compute_hashes(self, image_path):
        """
        Вычисляет перцептуальные хэши
        
        Returns:
            dict: {'phash': int, 'dhash': int, 'ahash': int}
        """
        try:
            img = Image.open(image_path)
            
            return {
                'phash': int(str(imagehash.phash(img, hash_size=self.hash_size)), 16),
                'dhash': int(str(imagehash.dhash(img, hash_size=self.hash_size)), 16),
                'ahash': int(str(imagehash.average_hash(img, hash_size=self.hash_size)), 16),
            }
        except Exception as e:
            raise Exception(f"Ошибка вычисления хэшей: {e}")
    
    @staticmethod
    def hamming_distance(hash1, hash2):
        """
        Расстояние Хэмминга между хэшами
        
        Returns:
            int: количество различающихся бит
        """
        return bin(hash1 ^ hash2).count('1')
    
    def compute_clip_embedding(self, image_path, model=None):
        """
        Вычисляет CLIP эмбеддинг (512-мерный вектор)
        
        Args:
            image_path: путь к изображению
            model: SentenceTransformer модель (передавать для переиспользования)
            
        Returns:
            np.ndarray: вектор (512,)
        """
        try:
            from sentence_transformers import SentenceTransformer
            
            if model is None:
                model = SentenceTransformer('clip-ViT-B-32')
            
            img = Image.open(image_path).convert('RGB')
            embedding = model.encode([img], convert_to_numpy=True, normalize_embeddings=True)[0]
            
            return embedding
            
        except Exception as e:
            raise Exception(f"Ошибка вычисления CLIP эмбеддинга: {e}")
    
    def compute_ssim(self, img1_path, img2_path):
        """
        Структурное сходство (SSIM) между двумя изображениями
        
        Returns:
            float: значение 0-1 (1 = идентичны)
        """
        try:
            # Загружаем изображения
            img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)
            img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)
            
            # Приводим к одному размеру
            height = min(img1.shape[0], img2.shape[0])
            width = min(img1.shape[1], img2.shape[1])
            
            img1 = cv2.resize(img1, (width, height))
            img2 = cv2.resize(img2, (width, height))
            
            # Вычисляем SSIM
            score, _ = ssim(img1, img2, full=True)
            
            return float(score)
            
        except Exception as e:
            return 0.0
    
    def compare_images(self, img1_path, img2_path, use_clip=True):
        """
        Комплексное сравнение двух изображений
        
        Returns:
            dict: {'phash_distance', 'ssim', 'clip_similarity', 'is_duplicate', 'confidence'}
        """
        result = {
            'phash_distance': None,
            'ssim': None,
            'clip_similarity': None,
            'is_duplicate': False,
            'confidence': 0.0
        }
        
        # 1. Perceptual hash (быстро)
        hashes1 = self.compute_hashes(img1_path)
        hashes2 = self.compute_hashes(img2_path)
        
        phash_dist = self.hamming_distance(hashes1['phash'], hashes2['phash'])
        result['phash_distance'] = phash_dist
        
        # Если pHash расстояние < 10, считаем похожими
        if phash_dist < 10:
            # 2. SSIM для точного сравнения
            result['ssim'] = self.compute_ssim(img1_path, img2_path)
            
            # 3. CLIP эмбеддинг (опционально, медленнее)
            if use_clip and result['ssim'] > 0.7:
                emb1 = self.compute_clip_embedding(img1_path)
                emb2 = self.compute_clip_embedding(img2_path)
                result['clip_similarity'] = float(np.dot(emb1, emb2))
            
            # Определяем дубликат
            if phash_dist <= 5 and result['ssim'] > 0.9:
                result['is_duplicate'] = True
                result['confidence'] = 0.95
            elif phash_dist <= 8 and result['ssim'] > 0.85:
                result['is_duplicate'] = True
                result['confidence'] = 0.85
        
        return result
```

---

### ЭТАП 4: Интеграция в Celery задачу (30 мин)

#### 4.1 Обновить задачу обработки

**Добавить в `Folder/documents/tasks.py`:**
```python
from documents.image_extractor import ImageExtractor
from documents.image_processor import ImageProcessor
from documents.image_models import DocumentImage, ImageSimilarity


@shared_task(bind=True, max_retries=3)
def process_images_plagiarism(self, document_id):
    """
    Извлечение и анализ изображений из документа
    
    Args:
        document_id: ID документа
    """
    try:
        doc = Document.objects.get(id=document_id)
        
        # 1. Извлекаем изображения
        file_path = doc.data.path
        output_dir = os.path.join('media', 'extracted_images', f'doc_{document_id}')
        
        extractor = ImageExtractor(min_width=150, min_height=150)
        extracted_images = extractor.extract(file_path, output_dir)
        
        if not extracted_images:
            return {'status': 'no_images', 'message': 'Изображения не найдены'}
        
        # 2. Обрабатываем каждое изображение
        processor = ImageProcessor()
        clip_model = None  # Загружаем один раз
        
        for img_data in extracted_images:
            # Вычисляем хэши
            hashes = processor.compute_hashes(img_data['path'])
            
            # Вычисляем CLIP эмбеддинг
            embedding = processor.compute_clip_embedding(img_data['path'], clip_model)
            
            # Сохраняем в БД
            doc_image = DocumentImage.objects.create(
                document=doc,
                page_number=img_data['page'],
                image_index=img_data['index'],
                image_file=img_data['path'],
                width=img_data['width'],
                height=img_data['height'],
                format=img_data['format'],
                size_bytes=img_data['size'],
                phash=hashes['phash'],
                dhash=hashes['dhash'],
                ahash=hashes['ahash'],
                embedding=embedding.tolist()
            )
        
        # 3. Поиск похожих изображений
        duplicates_found = find_similar_images(document_id)
        
        return {
            'status': 'success',
            'images_extracted': len(extracted_images),
            'duplicates_found': duplicates_found
        }
        
    except Exception as exc:
        raise self.retry(exc=exc)


def find_similar_images(document_id):
    """
    Ищет похожие изображения для всех картинок документа
    
    Returns:
        int: количество найденных дубликатов
    """
    doc_images = DocumentImage.objects.filter(document_id=document_id)
    processor = ImageProcessor()
    duplicates_count = 0
    
    for img in doc_images:
        # Быстрый поиск по pHash (Hamming distance < 10)
        # В реальности нужен специальный индекс или BK-tree
        similar_candidates = DocumentImage.objects.exclude(
            document_id=document_id
        ).exclude(
            phash__isnull=True
        )
        
        for candidate in similar_candidates:
            hamming = processor.hamming_distance(img.phash, candidate.phash)
            
            if hamming < 10:
                # Детальное сравнение
                comparison = processor.compare_images(
                    img.image_file.path,
                    candidate.image_file.path,
                    use_clip=True
                )
                
                if comparison['is_duplicate']:
                    # Сохраняем найденное совпадение
                    ImageSimilarity.objects.get_or_create(
                        image1=img,
                        image2=candidate,
                        defaults={
                            'phash_distance': hamming,
                            'cosine_similarity': comparison.get('clip_similarity', 0),
                            'ssim_score': comparison.get('ssim'),
                            'is_duplicate': True,
                            'confidence': comparison['confidence']
                        }
                    )
                    duplicates_count += 1
    
    return duplicates_count
```

#### 4.2 Интегрировать в основную задачу

**Обновить `process_document_plagiarism` в `tasks.py`:**
```python
# После шага 3 (анализ плагиата текста)
# Добавляем шаг 4:

# Шаг 4: Обработка изображений (асинхронно)
process_images_plagiarism.delay(document_id)
```

---

### ЭТАП 5: API и UI (45 мин)

#### 5.1 Создать view для отображения

**Добавить в `Folder/documents/views.py`:**
```python
@login_required
def document_images(request, document_id):
    """Показать изображения документа и их анализ"""
    doc = get_object_or_404(Document, id=document_id)
    
    # Проверяем права доступа
    if not (request.user.is_staff or doc.user == request.user):
        return HttpResponseForbidden()
    
    images = DocumentImage.objects.filter(document=doc).order_by('page_number', 'image_index')
    
    # Для каждого изображения получаем похожие
    images_with_duplicates = []
    for img in images:
        duplicates = ImageSimilarity.objects.filter(
            image1=img,
            is_duplicate=True
        ).select_related('image2__document')[:5]
        
        images_with_duplicates.append({
            'image': img,
            'duplicates': duplicates
        })
    
    context = {
        'document': doc,
        'images_data': images_with_duplicates,
        'total_images': images.count()
    }
    
    return render(request, 'documents/document_images.html', context)
```

#### 5.2 Создать шаблон

**Файл `Folder/documents/templates/documents/document_images.html`:**
```html
{% extends 'base.html' %}

{% block content %}
<div class="container">
    <h1>Изображения: {{ document.name }}</h1>
    
    <div class="stats">
        <p>Всего изображений: {{ total_images }}</p>
    </div>
    
    {% for item in images_data %}
    <div class="image-card">
        <div class="image-preview">
            <img src="{{ item.image.image_file.url }}" alt="Image {{ item.image.id }}">
            <p>Страница {{ item.image.page_number }}, Изображение {{ item.image.image_index }}</p>
            <p>Размер: {{ item.image.width }}x{{ item.image.height }}</p>
        </div>
        
        {% if item.duplicates %}
        <div class="duplicates">
            <h3>⚠️ Найдены похожие изображения ({{ item.duplicates|length }}):</h3>
            {% for dup in item.duplicates %}
            <div class="duplicate-item">
                <img src="{{ dup.image2.image_file.url }}" alt="Duplicate">
                <p>
                    Документ: <a href="{% url 'documents:download_file' dup.image2.document.id %}">{{ dup.image2.document.name }}</a>
                </p>
                <p>Схожесть: {{ dup.confidence|floatformat:2 }}</p>
                <p>SSIM: {{ dup.ssim_score|floatformat:3 }}</p>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <p class="no-duplicates">✅ Уникальное изображение</p>
        {% endif %}
    </div>
    {% endfor %}
</div>
{% endblock %}
```

---

### ЭТАП 6: Оптимизация поиска через pgvector (30 мин)

#### 6.1 Использовать pgvector для CLIP векторов

**Обновить `find_similar_images()` для использования ANN (Approximate Nearest Neighbor):**
```python
def find_similar_images_fast(document_id, threshold=0.85):
    """
    Быстрый поиск похожих изображений через pgvector
    
    Args:
        document_id: ID документа
        threshold: порог косинусного сходства
    """
    from django.db import connection
    
    doc_images = DocumentImage.objects.filter(document_id=document_id)
    processor = ImageProcessor()
    duplicates_count = 0
    
    for img in doc_images:
        if img.embedding is None:
            continue
        
        # Быстрый ANN поиск через pgvector
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, document_id, 
                       embedding <=> %s::vector AS distance,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM document_images
                WHERE id != %s
                  AND document_id != %s
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT 10
            """, [img.embedding, img.embedding, img.id, document_id, img.embedding])
            
            results = cursor.fetchall()
        
        for similar_id, similar_doc_id, distance, similarity in results:
            if similarity >= threshold:
                candidate = DocumentImage.objects.get(id=similar_id)
                
                # Уточняем через pHash
                hamming = processor.hamming_distance(img.phash, candidate.phash)
                
                if hamming < 10:
                    # Финальная проверка через SSIM
                    ssim_score = processor.compute_ssim(
                        img.image_file.path,
                        candidate.image_file.path
                    )
                    
                    if ssim_score > 0.85:
                        ImageSimilarity.objects.get_or_create(
                            image1=img,
                            image2=candidate,
                            defaults={
                                'phash_distance': hamming,
                                'cosine_similarity': similarity,
                                'ssim_score': ssim_score,
                                'is_duplicate': True,
                                'confidence': (similarity + ssim_score) / 2
                            }
                        )
                        duplicates_count += 1
    
    return duplicates_count
```

#### 6.2 Создать индексы

**SQL для pgvector:**
```sql
-- HNSW индекс для быстрого ANN поиска
CREATE INDEX IF NOT EXISTS image_embedding_hnsw_idx 
ON document_images 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- B-tree индекс для pHash
CREATE INDEX IF NOT EXISTS image_phash_idx 
ON document_images (phash);
```

---

## 📊 ОБРАБОТКА ТАБЛИЦ

### Текущая реализация:
✅ Текст из таблиц **УЖЕ ИЗВЛЕКАЕТСЯ** в `docx_extractor.py`:
```python
# Извлекаем текст из таблиц
for table in doc.tables:
    for row in table.rows:
        row_text = []
        for cell in row.cells:
            cell_text = cell.text.strip()
            if cell_text:
                row_text.append(cell_text)
        if row_text:
            tables_text.append(' | '.join(row_text))
```

### Улучшения для таблиц:

#### 1. Структурное сравнение таблиц

**Создать `Folder/documents/table_comparator.py`:**
```python
"""
Сравнение структуры и содержимого таблиц
"""

def extract_tables_structure(docx_path):
    """
    Извлекает таблицы с сохранением структуры
    
    Returns:
        List[dict]: [{
            'rows': int,
            'cols': int,
            'headers': List[str],
            'data': List[List[str]],
            'hash': str  # Хэш структуры
        }]
    """
    from docx import Document as DocxDocument
    import hashlib
    
    doc = DocxDocument(docx_path)
    tables_data = []
    
    for table in doc.tables:
        rows_count = len(table.rows)
        cols_count = len(table.columns) if table.rows else 0
        
        # Извлекаем заголовки (первая строка)
        headers = []
        if rows_count > 0:
            headers = [cell.text.strip() for cell in table.rows[0].cells]
        
        # Извлекаем данные
        data = []
        for row in table.rows[1:]:  # Пропускаем заголовки
            row_data = [cell.text.strip() for cell in row.cells]
            data.append(row_data)
        
        # Хэш структуры (размеры + заголовки)
        structure_str = f"{rows_count}x{cols_count}_{'-'.join(headers)}"
        table_hash = hashlib.md5(structure_str.encode()).hexdigest()
        
        tables_data.append({
            'rows': rows_count,
            'cols': cols_count,
            'headers': headers,
            'data': data,
            'hash': table_hash
        })
    
    return tables_data


def compare_tables(table1, table2):
    """
    Сравнивает две таблицы
    
    Returns:
        dict: {'structure_match': bool, 'data_similarity': float}
    """
    # 1. Структурное совпадение
    structure_match = (
        table1['rows'] == table2['rows'] and
        table1['cols'] == table2['cols'] and
        table1['headers'] == table2['headers']
    )
    
    # 2. Сходство данных
    if not structure_match:
        return {'structure_match': False, 'data_similarity': 0.0}
    
    total_cells = 0
    matching_cells = 0
    
    for row1, row2 in zip(table1['data'], table2['data']):
        for cell1, cell2 in zip(row1, row2):
            total_cells += 1
            if cell1.lower() == cell2.lower():
                matching_cells += 1
    
    data_similarity = matching_cells / total_cells if total_cells > 0 else 0.0
    
    return {
        'structure_match': True,
        'data_similarity': data_similarity
    }
```

---

## 🎨 ИНТЕГРАЦИЯ В UI

### 1. Добавить кнопку "Изображения" в кабинете

```html
<!-- В cab.html -->
<button type="button" class="more-btns__link">
  <a href="{% url 'documents:document_images' document.id %}">
    📷 Изображения ({{ document.images.count }})
  </a>
</button>
```

### 2. Показывать результат в карточке документа

```html
<!-- Индикатор найденных дубликатов изображений -->
{% if document.images.count > 0 %}
  {% with duplicates=document.images.filter(similarities_as_img1__is_duplicate=True).count %}
    {% if duplicates > 0 %}
      <span class="image-duplicates-warning">
        ⚠️ {{ duplicates }} совпадений изображений
      </span>
    {% endif %}
  {% endwith %}
{% endif %}
```

---

## 🔥 ПРОИЗВОДИТЕЛЬНОСТЬ

### Оптимизации:

**1. Кэширование CLIP модели**
```python
# Загружаем модель один раз и переиспользуем
_clip_model_cache = None

def get_clip_model():
    global _clip_model_cache
    if _clip_model_cache is None:
        from sentence_transformers import SentenceTransformer
        _clip_model_cache = SentenceTransformer('clip-ViT-B-32')
    return _clip_model_cache
```

**2. Батчинг обработки**
```python
# Обрабатываем изображения пачками по 10
for i in range(0, len(images), 10):
    batch = images[i:i+10]
    embeddings = model.encode([img for img in batch])
```

**3. pgvector ANN индекс**
- HNSW индекс для векторного поиска (~1000x быстрее)
- B-tree для pHash (~100x быстрее)

**4. Фоновая обработка**
- Извлечение изображений в отдельной Celery задаче
- Приоритет ниже чем у текстового анализа

---

## 📐 АРХИТЕКТУРА ПОЛНОЙ СИСТЕМЫ

```
Загрузка PDF/DOCX
        │
        ├─→ Извлечение ТЕКСТА
        │   ├─→ Векторизация (sentence-transformers)
        │   ├─→ Поиск похожих текстов
        │   └─→ Расчёт оригинальности ✅
        │
        └─→ Извлечение ИЗОБРАЖЕНИЙ
            ├─→ Вычисление pHash/dHash/aHash (быстро)
            ├─→ Вычисление CLIP embedding (медленно)
            ├─→ Поиск похожих:
            │   ├─→ pHash search (Hamming < 10)
            │   ├─→ CLIP ANN search (pgvector)
            │   └─→ Рефайн через SSIM
            └─→ Сохранение результатов ✅
```

---

## 💾 НОВАЯ СТРУКТУРА БД

```sql
-- Таблица изображений
CREATE TABLE document_images (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES "Document"(id),
    page_number INTEGER,
    image_index INTEGER,
    image_file VARCHAR(255),
    width INTEGER,
    height INTEGER,
    format VARCHAR(10),
    size_bytes INTEGER,
    phash BIGINT,          -- Perceptual hash
    dhash BIGINT,          -- Difference hash  
    ahash BIGINT,          -- Average hash
    embedding vector(512), -- CLIP эмбеддинг
    created_at TIMESTAMP
);

-- Индексы
CREATE INDEX image_phash_idx ON document_images (phash);
CREATE INDEX image_embedding_hnsw_idx ON document_images 
    USING hnsw (embedding vector_cosine_ops);

-- Таблица схожести
CREATE TABLE image_similarities (
    id SERIAL PRIMARY KEY,
    image1_id INTEGER REFERENCES document_images(id),
    image2_id INTEGER REFERENCES document_images(id),
    phash_distance INTEGER,
    cosine_similarity FLOAT,
    ssim_score FLOAT,
    is_duplicate BOOLEAN,
    confidence FLOAT,
    created_at TIMESTAMP,
    UNIQUE(image1_id, image2_id)
);
```

---

## 🎯 ИТОГОВЫЙ WORKFLOW

### Для пользователя:
1. Загружает курсовую работу (PDF/DOCX)
2. Система извлекает текст + изображения
3. Анализирует текст на плагиат ✅
4. Анализирует изображения на дубликаты 📸
5. Показывает общий отчёт:
   - Оригинальность текста: 85%
   - Найдено совпадений изображений: 3
   - Риск: medium

### Для преподавателя:
1. Видит список документов с индикаторами
2. Кликает "Изображения" → видит все картинки
3. Для каждой картинки видит похожие из других работ
4. Может сравнить визуально и принять решение

---

## 📊 ТАБЛИЦЫ: КАК ОБРАБАТЫВАЮТСЯ

### Текущая система (текст):
Таблицы извлекаются как текст: `Заголовок1 | Заголовок2 | ... \n Данные1 | Данные2 | ...`

Затем сравниваются как обычный текст через shingles.

### Улучшенная система (структурное сравнение):

**1. Извлечение:**
- Сохраняем структуру: rows x cols
- Сохраняем заголовки отдельно
- Сохраняем данные как матрицу

**2. Сравнение:**
```python
# Если структура идентична (rows, cols, headers)
if tables_match_structure(t1, t2):
    # Сравниваем содержимое ячеек
    cell_similarity = compare_cells(t1.data, t2.data)
    
    if cell_similarity > 0.9:
        # ПЛАГИАТ - скопирована вся таблица
        return 0% originality
    elif cell_similarity > 0.7:
        # ПОДОЗРЕНИЕ - большая часть данных совпадает
        return low_originality
```

**3. Визуализация:**
- Подсветка совпадающих ячеек красным
- Diff-view для таблиц
- Процент совпадения по ячейкам

---

## 🚀 ЭТАПЫ ВНЕДРЕНИЯ

### Минимальная версия (1-2 дня):
1. ✅ Извлечение изображений из PDF/DOCX
2. ✅ pHash вычисление
3. ✅ Простой поиск дубликатов (Hamming < 5)
4. ✅ UI для просмотра

### Средняя версия (+2-3 дня):
5. ✅ CLIP эмбеддинги
6. ✅ pgvector ANN поиск
7. ✅ SSIM рефайн
8. ✅ Асинхронная обработка

### Полная версия (+3-5 дней):
9. ✅ Структурное сравнение таблиц
10. ✅ Diff-view для таблиц
11. ✅ ORB feature matching (устойчивость к поворотам)
12. ✅ Детекция модификаций (фильтры, кадрирование)
13. ✅ ML классификатор "подозрительности"

---

## 💡 ДОПОЛНИТЕЛЬНЫЕ ВОЗМОЖНОСТИ

### 1. Детекция скриншотов
Распознавание что изображение - это скриншот кода/текста, и проверка текста на нём через OCR (Tesseract).

### 2. Reverse image search
Поиск изображений в интернете (Google/Yandex Images API)

### 3. Watermark detection
Определение вотермарков/логотипов на изображениях

### 4. Chart/Graph recognition
Специальная обработка графиков и диаграмм (сравнение данных, а не пикселей)

---

## ⚠️ ВАЖНЫЕ ЗАМЕЧАНИЯ

### Производительность:
- **CLIP эмбеддинг:** ~200-500ms на изображение
- **pHash:** ~10-50ms на изображение
- **SSIM:** ~50-200ms на пару
- **Для 10 изображений:** ~30-60 секунд общее время

**Решение:** Celery с низким приоритетом, обрабатывать после текста.

### Хранилище:
- Изображение (~200 KB) × 10 шт × 1000 документов = **~2 GB**
- CLIP вектор (512 × 4 байта) × 10 изображений × 1000 = **~20 MB**

**Решение:** Периодическая очистка старых изображений, компрессия.

### Ложные срабатывания:
- Шаблонные схемы из учебников (все используют)
- Стандартные иконки/логотипы

**Решение:** Whitelist популярных изображений, порог confidence > 0.9.

---

## ✅ ИТОГ

### DOCX поддержка - ГОТОВА ✅
- Добавлен `python-docx`
- Создан `docx_extractor.py`
- Обновлены формы и валидация
- Обновлены задачи обработки
- Шаблоны с примечанием "PDF, DOCX"

### Проверка изображений - ПЛАН ГОТОВ 📋
- Детальная архитектура
- Код примеров всех компонентов
- Оптимизация через pgvector
- UI/UX решения
- Оценка времени: 5-10 дней полной реализации

### Таблицы - УЖЕ ОБРАБАТЫВАЮТСЯ ✅
- Текст извлекается
- Сравнивается через shingles
- Можно улучшить структурным сравнением

Готов реализовать проверку изображений если нужно - скажите и начну!
