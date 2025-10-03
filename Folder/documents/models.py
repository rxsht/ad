import os
import time
import json
import numpy as np
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from documents import text_clining, vector, sim_cos
from users.models import User
from django.contrib import admin
from django.utils.html import format_html
from documents.vector_models import DocumentVector, DocumentSimilarity, DocumentBatch, DocumentProcessingQueue

# Глобальные переменные для косинусного сходства и параметров
COSIM_THRESHOLD = 0.9  # Порог схожести для определения плагиата
WORDS_PER_BLOCK = 300  # Количество слов для каждого блока (можно настроить)


# Модель для хранения статуса документа
class Status(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Название')
    html_clase = models.CharField(max_length=100, unique=True, verbose_name='html клас', default='queue')

    class Meta:
        db_table = 'status'
        verbose_name = 'Статус'
        verbose_name_plural = 'Статусы'

    def __str__(self):
        return self.name


# Модель для хранения типа работы
class Type(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Название')

    class Meta:
        db_table = 'type'
        verbose_name = 'Тип работы'
        verbose_name_plural = 'Типы работ'

    def __str__(self):
        return self.name


# Модель для хранения похожих документов
class SimilarDocument(models.Model):
    document = models.ForeignKey('Document', on_delete=models.CASCADE, related_name='similar_documents')
    similar_document = models.ForeignKey('Document', on_delete=models.CASCADE, related_name='similar_to')
    similarity_score = models.FloatField(verbose_name='Схожесть')

    class Meta:
        db_table = 'similar_document'
        verbose_name = 'Похожий документ'
        verbose_name_plural = 'Похожие документы'

    def __str__(self):
        return f"{self.document.name} -> {self.similar_document.name} (Схожесть: {self.similarity_score})"


# Основная модель для хранения документов
class Document(models.Model):
    user = models.ForeignKey(to=User, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True, unique=True, verbose_name='Название')
    result = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='Оригинальность')
    status = models.ForeignKey(to=Status, default=1, on_delete=models.CASCADE)
    type = models.ForeignKey(to=Type, on_delete=models.CASCADE, default=1)
    time_created = models.DateTimeField(auto_now_add=True, verbose_name='Дата и время загрузки документа')
    data = models.FileField(upload_to="pdf_files/", verbose_name='документ')
    txt_file = models.FileField(upload_to='txt_files/', blank=True, null=True)
    vector = models.TextField(blank=True, null=True, verbose_name='Векторное представление текста (JSON)')
    last_status_changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='status_changed_docs')

    class Meta:
        db_table = 'Document'
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'
        ordering = ["time_created"]

    def __str__(self):
        return self.name

    def get_text_preview(self):
        """Возвращает предварительный просмотр текста из файла."""
        if self.txt_file:
            try:
                with open(self.txt_file.path, 'r', encoding='utf-8') as text_file:
                    return text_file.read()[:200] + '...'  # Предварительный просмотр
            except Exception:
                return "Не удалось загрузить текст."
        return "Текстовый файл не найден."

    def get_vector_array(self):
        """Возвращает вектор как numpy array."""
        if self.vector:
            try:
                vector_data = json.loads(self.vector)
                return np.array(vector_data)
            except (json.JSONDecodeError, ValueError):
                return None
        return None

    def set_vector_array(self, vector_array):
        """Устанавливает вектор из numpy array."""
        if vector_array is not None:
            self.vector = json.dumps(vector_array.tolist())
        else:
            self.vector = None


    def calculate_originality(self):
        """Метод для вычисления оригинальности с использованием косинусного сходства."""
        # Проверяем, рассчитан ли уже результат
        if self.result is not None:
            return  # Если результат уже есть, не пересчитываем оригинальность
        
        start_time = time.time()

        if self.vector:
            # Получаем вектор текущего документа
            current_vector = self.get_vector_array()
            if current_vector is None:
                self.result = 100.0
                new_status = Status.objects.get(pk=2)
                self.status = new_status
                self.save(update_fields=['result', 'status'])
                return

            # Находим похожие документы по косинусному сходству
            similar_docs = []
            all_docs = Document.objects.exclude(id=self.pk).exclude(vector__isnull=True)
            
            for doc in all_docs:
                doc_vector = doc.get_vector_array()
                if doc_vector is not None:
                    # Вычисляем косинусное сходство
                    similarity = self._cosine_similarity(current_vector, doc_vector)
                    if similarity > 0.7:  # Порог схожести
                        similar_docs.append((doc, similarity))

            # Сортируем по убыванию схожести и берем топ-5
            similar_docs.sort(key=lambda x: x[1], reverse=True)
            similar_docs = similar_docs[:5]

            if not similar_docs:
                self.result = 100.0
            else:
                # Используем текстовый анализ для точного расчета
                def get_file_text(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            return file.read()
                    except:
                        return ""
                
                if self.txt_file:
                    self_text = get_file_text(self.txt_file.path)
                    similar_texts = [get_file_text(doc[0].txt_file.path) for doc in similar_docs if doc[0].txt_file]
                    
                    if similar_texts:
                        originality = sim_cos.calculate_originality_large_texts(self_text, similar_texts, shingle_size=1)
                        self.result = max(0.0, min(100.0, originality))  # Ограничиваем от 0 до 100
                    else:
                        self.result = 100.0
                else:
                    self.result = 100.0

            new_status = Status.objects.get(pk=2)
            self.status = new_status
            self.save(update_fields=['result', 'status'])
        else:
            # Если нет вектора, устанавливаем оригинальность 100%
            self.result = 100.0
            new_status = Status.objects.get(pk=2)
            self.status = new_status
            self.save(update_fields=['result', 'status'])

        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Время расчета оригинальности текста: {elapsed_time:.4f} секунд")

    def _cosine_similarity(self, vec1, vec2):
        """Вычисляет косинусное сходство между двумя векторами."""
        try:
            # Нормализуем векторы
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Вычисляем косинусное сходство
            similarity = np.dot(vec1, vec2) / (norm1 * norm2)
            return float(similarity)
        except:
            return 0.0

@receiver(post_save, sender=Document)
def create_text_document(sender, instance, created, **kwargs):
    if created:
        try:
            text_content = text_clining.clean_text_from_pdf(os.path.join("media", instance.data.path))
            txt_filename = f"{instance.name}.txt"
            txt_file_path = os.path.join("media", "txt_files", txt_filename)

            with open(txt_file_path, "w", encoding='utf-8') as text_file:
                text_file.write(text_content)
                
            instance.txt_file = f"txt_files/{txt_filename}"

            # Обрабатываем текст и создаем вектор
            try:
                vector_array = vector.process_text(txt_file_path)
                instance.set_vector_array(vector_array)
            except Exception as e:
                print(f"Ошибка при создании вектора: {e}")
                instance.vector = None
            
            instance.save()

        except Exception as e:
            print(f"Произошла ошибка при извлечении текста: {e}")


@receiver(post_save, sender=Document)
def calculate_originality_on_save(sender, instance, created, **kwargs):
    if created:
        instance.calculate_originality()


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_text_preview', 'status', 'time_created')

    def get_text_preview(self, obj):
        return format_html("<pre>{}</pre>", obj.get_text_preview())

    get_text_preview.short_description = 'Предварительный просмотр текста'


@admin.register(SimilarDocument)
class SimilarDocumentAdmin(admin.ModelAdmin):
    list_display = ('document', 'similar_document', 'similarity_score')