"""
Векторные модели для PostgreSQL с pgvector
"""

import numpy as np
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from pgvector.django import VectorField, IvfflatIndex, HnswIndex
from users.models import User


class DocumentVector(models.Model):
    """
    Модель для хранения векторных представлений документов
    """
    document = models.OneToOneField(
        'Document', 
        on_delete=models.CASCADE, 
        related_name='document_vector'
    )
    
    # Векторное представление документа (384 измерения для sentence-transformers)
    vector = VectorField(dimensions=384, null=True, blank=True)
    
    # Нормализованный вектор для быстрого косинусного сходства
    normalized_vector = VectorField(dimensions=384, null=True, blank=True)
    
    # Метаданные для оптимизации
    vector_norm = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'document_vectors'
        indexes = [
            # Индекс по времени создания
            models.Index(fields=['created_at'], name='vector_created_idx'),
        ]
    
    def set_vector(self, vector_array):
        """Устанавливает вектор и вычисляет нормализованную версию"""
        if vector_array is not None:
            vector_array = np.array(vector_array, dtype=np.float32)
            self.vector = vector_array.tolist()
            
            # Нормализуем вектор для косинусного сходства
            norm = np.linalg.norm(vector_array)
            if norm > 0:
                self.normalized_vector = (vector_array / norm).tolist()
                self.vector_norm = float(norm)
            else:
                self.normalized_vector = None
                self.vector_norm = 0.0
    
    def get_vector(self):
        """Возвращает вектор как numpy array"""
        if self.vector:
            return np.array(self.vector, dtype=np.float32)
        return None
    
    def get_normalized_vector(self):
        """Возвращает нормализованный вектор"""
        if self.normalized_vector:
            return np.array(self.normalized_vector, dtype=np.float32)
        return None


class DocumentSimilarity(models.Model):
    """
    Модель для кэширования результатов сравнения документов
    """
    document1 = models.ForeignKey(
        'Document', 
        on_delete=models.CASCADE, 
        related_name='similarities_as_doc1'
    )
    document2 = models.ForeignKey(
        'Document', 
        on_delete=models.CASCADE, 
        related_name='similarities_as_doc2'
    )
    
    # Различные метрики схожести
    cosine_similarity = models.FloatField()
    jaccard_similarity = models.FloatField()
    dice_similarity = models.FloatField()
    levenshtein_similarity = models.FloatField()
    
    # Итоговая взвешенная схожесть
    weighted_similarity = models.FloatField()
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True)
    is_paraphrasing = models.BooleanField(default=False)
    confidence_score = models.FloatField(default=0.0)
    
    class Meta:
        db_table = 'document_similarities'
        unique_together = [['document1', 'document2']]
        indexes = [
            models.Index(fields=['weighted_similarity'], name='similarity_weighted_idx'),
            models.Index(fields=['cosine_similarity'], name='similarity_cosine_idx'),
            models.Index(fields=['created_at'], name='similarity_created_idx'),
        ]
    
    def __str__(self):
        return f"{self.document1.name} <-> {self.document2.name}: {self.weighted_similarity:.3f}"


class DocumentBatch(models.Model):
    """
    Модель для отслеживания пакетной обработки документов
    """
    BATCH_STATUS_CHOICES = [
        ('pending', 'Ожидает обработки'),
        ('processing', 'Обрабатывается'),
        ('completed', 'Завершено'),
        ('failed', 'Ошибка'),
    ]
    
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=BATCH_STATUS_CHOICES, default='pending')
    total_documents = models.IntegerField(default=0)
    processed_documents = models.IntegerField(default=0)
    failed_documents = models.IntegerField(default=0)
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Метаданные
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'document_batches'
        indexes = [
            models.Index(fields=['status'], name='batch_status_idx'),
            models.Index(fields=['created_at'], name='batch_created_idx'),
        ]
    
    def __str__(self):
        return f"Batch {self.name}: {self.status}"


class DocumentProcessingQueue(models.Model):
    """
    Очередь для обработки документов
    """
    PRIORITY_CHOICES = [
        (1, 'Низкий'),
        (2, 'Средний'),
        (3, 'Высокий'),
        (4, 'Критический'),
    ]
    
    document = models.ForeignKey('Document', on_delete=models.CASCADE)
    batch = models.ForeignKey(DocumentBatch, on_delete=models.CASCADE, null=True, blank=True)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)
    status = models.CharField(max_length=20, default='pending')
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Метаданные
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'document_processing_queue'
        indexes = [
            models.Index(fields=['status', 'priority'], name='queue_status_priority_idx'),
            models.Index(fields=['created_at'], name='queue_created_idx'),
        ]
        ordering = ['-priority', 'created_at']
    
    def __str__(self):
        return f"Queue: {self.document.name} ({self.status})"
