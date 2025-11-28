"""
Продвинутый детектор плагиата с множественными метриками
"""

import os
import re
import numpy as np
from typing import List, Tuple, Dict
from collections import Counter
from django.conf import settings

from documents.models import Document
from documents.sim_cos import (
    calculate_originality_large_texts, 
    generate_hashed_shingles, 
    coef_similarity_hashed,
    calculate_similarity_by_source,
    detect_citations
)
from documents.utils_cache import get_cached_vector, cache_vector, get_cached_similarity, cache_similarity_result
from .base_detector import BasePlagiarismDetector


class AdvancedPlagiarismDetector(BasePlagiarismDetector):
    """Продвинутый класс для выявления плагиата в текстах"""
    
    def __init__(self):
        super().__init__()
        self.shingle_sizes = [1, 3, 5]  # Разные размеры шинглов
        self.similarity_threshold = 0.6  # Порог схожести для векторов
        self.originality_threshold = 85.0  # Порог оригинальности
        self.min_text_length = 100  # Минимальная длина текста для анализа
        
    def preprocess_text(self, text: str) -> str:
        """Предобработка текста для улучшения точности сравнения"""
        # Приводим к нижнему регистру
        text = text.lower()
        
        # Удаляем лишние пробелы и переносы строк
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def calculate_text_similarity(self, text1: str, text2: str) -> Dict:
        """Вычисляет схожесть между двумя текстами различными методами"""
        # Предобрабатываем тексты
        text1_clean = self.preprocess_text(text1)
        text2_clean = self.preprocess_text(text2)
        
        results = {}
        
        # 1. Схожесть по шинглам разных размеров
        for shingle_size in self.shingle_sizes:
            shingles1 = generate_hashed_shingles(text1_clean, shingle_size)
            shingles2 = generate_hashed_shingles(text2_clean, shingle_size)
            
            if shingles1 and shingles2:
                similarity = coef_similarity_hashed(shingles1, shingles2)
                results[f'shingle_{shingle_size}'] = float(similarity)
        
        # 2. Схожесть по словам
        words1 = set(text1_clean.split())
        words2 = set(text2_clean.split())
        
        if words1 and words2:
            word_intersection = len(words1 & words2)
            word_union = len(words1 | words2)
            results['word_similarity'] = word_intersection / word_union if word_union > 0 else 0
        
        # 3. Схожесть по символам
        char1 = Counter(text1_clean)
        char2 = Counter(text2_clean)
        
        char_intersection = sum((char1 & char2).values())
        char_union = sum((char1 | char2).values())
        results['char_similarity'] = char_intersection / char_union if char_union > 0 else 0
        
        # 4. Схожесть по предложениям
        sentences1 = [s.strip() for s in re.split(r'[.!?]+', text1_clean) if s.strip()]
        sentences2 = [s.strip() for s in re.split(r'[.!?]+', text2_clean) if s.strip()]
        
        if sentences1 and sentences2:
            sentence_similarities = []
            for sent1 in sentences1:
                for sent2 in sentences2:
                    if sent1 and sent2:
                        sent1_words = set(sent1.split())
                        sent2_words = set(sent2.split())
                        if sent1_words and sent2_words:
                            sim = len(sent1_words & sent2_words) / len(sent1_words | sent2_words)
                            sentence_similarities.append(sim)
            
            results['sentence_similarity'] = np.mean(sentence_similarities) if sentence_similarities else 0
        
        # Вычисляем общую схожесть как среднее взвешенное
        weights = {
            'shingle_1': 0.3,
            'shingle_3': 0.4,
            'shingle_5': 0.2,
            'word_similarity': 0.1
        }
        
        weighted_similarity = 0
        total_weight = 0
        
        for method, weight in weights.items():
            if method in results:
                weighted_similarity += results[method] * weight
                total_weight += weight
        
        results['overall_similarity'] = weighted_similarity / total_weight if total_weight > 0 else 0
        
        return results
    
    def detect_plagiarism(self, document_id: int) -> Dict:
        """Выявляет плагиат для конкретного документа с детальным анализом"""
        try:
            document = Document.objects.get(id=document_id)
            
            result = {
                'document_id': document_id,
                'document_name': document.name,
                'originality': 0.0,
                'similarity': 0.0,
                'similar_documents': [],
                'is_plagiarized': False,
                'plagiarism_risk': 'low',
                'detailed_analysis': {},
                'status': 'success',
                'message': ''
            }
            
            # --- ПРОВЕРКА ПО ИМЕНИ ФАЙЛА: если есть дубликаты по имени в общей базе → 0% ---
            # Общая база: документы с on_defense=True
            if document.data:
                try:
                    current_file_name = os.path.basename(document.data.name)
                    # Берём все документы из общей базы (отправленные на защиту), кроме текущего
                    all_docs_with_files = Document.objects.filter(on_defense=True)\
                                                           .exclude(id=document.id)\
                                                           .exclude(data='')\
                                                           .exclude(data__isnull=True)

                    exact_duplicates = []
                    for d in all_docs_with_files:
                        try:
                            if d.data:
                                other_file_name = os.path.basename(d.data.name)
                                if other_file_name == current_file_name:
                                    exact_duplicates.append(d)
                        except Exception:
                            continue

                    if exact_duplicates:
                        # Есть документы с таким же именем файла в общей базе → оригинальность 0%
                        result['originality'] = 0.0
                        result['similarity'] = 100.0
                        result['is_plagiarized'] = True
                        result['plagiarism_risk'] = 'very_high'
                        result['message'] = f'Найден(ы) документ(ы) с таким же именем файла ({current_file_name}) в общей базе. Оригинальность: 0%.'
                        result['source_matches'] = [
                            {
                                'document_id': d.id,
                                'document_name': d.name,
                                'file_name': current_file_name,
                            }
                            for d in exact_duplicates
                        ]
                        return result
                except Exception as e:
                    print(f"Ошибка при проверке имени файла: {e}")
            
            # Проверяем наличие TXT файла
            if not document.txt_file:
                result['status'] = 'error'
                result['message'] = 'TXT файл не найден'
                return result
            
            # Получаем путь к txt файлу (поддержка относительных и абсолютных путей)
            try:
                txt_path = document.txt_file.path
            except Exception:
                # Fallback если .path не работает
                txt_path = os.path.join(settings.MEDIA_ROOT, str(document.txt_file))
            
            if not os.path.exists(txt_path):
                result['status'] = 'error'
                result['message'] = f'TXT файл не существует: {txt_path}'
                return result
            
            # Читаем текст документа
            with open(txt_path, 'r', encoding='utf-8') as f:
                document_text = f.read()
            
            if len(document_text) < self.min_text_length:
                result['status'] = 'warning'
                result['message'] = f'Текст слишком короткий для анализа ({len(document_text)} символов)'
                return result
            
            # Находим похожие документы
            similar_docs = self._find_similar_documents(document)
            
            # Если векторы недоступны, используем текстовый анализ как fallback
            if not similar_docs and not document.vector:
                similar_docs = self._find_similar_documents_text_based(document, document_text)
            
            if not similar_docs:
                result['originality'] = 100.0
                result['similarity'] = 0.0
                result['citations'] = 0.0
                result['source_matches'] = []
                result['message'] = 'Документ оригинален - похожих документов не найдено'
                result['plagiarism_risk'] = 'very_low'
            else:
                # Детальный анализ с каждым похожим документом
                similarities = []
                similar_texts = []
                detailed_similarities = []
                
                for doc, vector_similarity in similar_docs:
                    if doc.txt_file:
                        # Получаем путь с обработкой ошибок
                        try:
                            similar_txt_path = doc.txt_file.path
                        except Exception:
                            similar_txt_path = os.path.join(settings.MEDIA_ROOT, str(doc.txt_file))
                        
                        if os.path.exists(similar_txt_path):
                            with open(similar_txt_path, 'r', encoding='utf-8') as f:
                                similar_text = f.read()
                            
                            # Детальный анализ схожести
                            detailed_sim = self.calculate_text_similarity(document_text, similar_text)
                            
                            similarities.append(detailed_sim['overall_similarity'])
                            detailed_similarities.append(detailed_sim)
                            similar_texts.append(similar_text)
                            
                            result['similar_documents'].append({
                                'id': doc.id,
                                'name': doc.name,
                                'vector_similarity': float(vector_similarity),
                                'text_similarity': detailed_sim['overall_similarity'],
                                'detailed_similarity': detailed_sim,
                                'originality': float(doc.result) if doc.result else 0.0
                            })
                
                if similar_texts:
                    # Рассчитываем оригинальность для КАЖДОГО похожего документа отдельно
                    # и берём МИНИМАЛЬНУЮ (худший случай)
                    originality_scores = []
                    source_matches = []  # Список совпадений по источникам
                    
                    for idx, (doc, vector_sim) in enumerate(similar_docs):
                        if idx < len(similar_texts):
                            similar_text = similar_texts[idx]
                            
                            # Рассчитываем оригинальность
                            originality = calculate_originality_large_texts(
                                document_text, 
                                [similar_text],  # Сравниваем с ОДНИМ документом
                                shingle_size=3
                            )
                            originality_scores.append(originality)
                            
                            # Рассчитываем процент совпадений с этим источником
                            match_percent = calculate_similarity_by_source(
                                document_text,
                                similar_text,
                                shingle_size=3
                            )
                            
                            # Рассчитываем процент цитирований
                            citation_percent = detect_citations(
                                document_text,
                                similar_text,
                                shingle_size=3
                            )
                            
                            # Сохраняем информацию об источнике
                            source_matches.append({
                                'document_id': doc.id,
                                'document_name': doc.name,
                                'match_percent': round(match_percent, 2),
                                'citation_percent': round(citation_percent, 2)
                            })
                    
                    # Берём минимальную оригинальность (максимальную схожесть)
                    result['originality'] = max(0.0, min(100.0, min(originality_scores)))
                    result['similarity'] = 100 - result['originality']
                    
                    # Рассчитываем общий процент цитирований
                    # Используем максимум из всех источников, так как цитирования могут перекрываться
                    # и сумма может превышать 100%
                    if source_matches:
                        # Берем максимальный процент цитирований среди всех источников
                        max_citation_percent = max([match['citation_percent'] for match in source_matches], default=0.0)
                        # Ограничиваем цитирования общим процентом совпадений
                        result['citations'] = round(min(max_citation_percent, result['similarity']), 2)
                        result['source_matches'] = source_matches
                    else:
                        result['citations'] = 0.0
                        result['source_matches'] = []
                    
                    # Определяем риск плагиата
                    max_similarity = max(similarities) if similarities else 0
                    avg_similarity = np.mean(similarities) if similarities else 0
                    
                    if max_similarity > 0.9:
                        result['plagiarism_risk'] = 'very_high'
                    elif max_similarity > 0.8:
                        result['plagiarism_risk'] = 'high'
                    elif max_similarity > 0.7:
                        result['plagiarism_risk'] = 'medium'
                    elif max_similarity > 0.5:
                        result['plagiarism_risk'] = 'low'
                    else:
                        result['plagiarism_risk'] = 'very_low'
                    
                    # Определяем, является ли документ плагиатом
                    result['is_plagiarized'] = (
                        result['originality'] < self.originality_threshold or 
                        max_similarity > 0.8
                    )
                    
                    # Детальная аналитика
                    result['detailed_analysis'] = {
                        'max_similarity': float(max_similarity),
                        'avg_similarity': float(avg_similarity),
                        'similar_documents_count': len(similar_docs),
                        'text_length': len(document_text),
                        'analysis_methods': list(detailed_similarities[0].keys()) if detailed_similarities and len(detailed_similarities) > 0 else []
                    }
                    
                    if result['is_plagiarized']:
                        result['message'] = f'⚠️ ВНИМАНИЕ: Документ может содержать плагиат! Оригинальность: {result["originality"]:.2f}%, Максимальная схожесть: {max_similarity:.2f}'
                    else:
                        result['message'] = f'✅ Документ оригинален. Оригинальность: {result["originality"]:.2f}%, Максимальная схожесть: {max_similarity:.2f}'
                else:
                    result['originality'] = 100.0
                    result['similarity'] = 0.0
                    result['citations'] = 0.0
                    result['source_matches'] = []
                    result['message'] = 'Документ оригинален - не удалось прочитать похожие документы'
                    result['plagiarism_risk'] = 'very_low'
            
            return result
            
        except Document.DoesNotExist:
            return {
                'document_id': document_id,
                'status': 'error',
                'message': f'Документ с ID {document_id} не найден'
            }
        except Exception as e:
            return {
                'document_id': document_id,
                'status': 'error',
                'message': f'Ошибка при анализе: {str(e)}'
            }
    
    def _find_similar_documents(self, document: Document) -> List[Tuple[Document, float]]:
        """Находит похожие документы по косинусному сходству векторов с кэшированием"""
        similar_docs = []
        
        if not document.vector:
            return similar_docs
        
        try:
            # Пробуем получить вектор из кэша
            current_vector = get_cached_vector(document.id)
            if current_vector is None:
                current_vector = document.get_vector_array()
                if current_vector is not None:
                    # Кэшируем вектор для будущих запросов
                    cache_vector(document.id, current_vector)
            
            if current_vector is None:
                return similar_docs
            
            # Берём только документы из общей базы (отправленные на защиту)
            # Документы пользователя также могут быть источниками (сравниваются между собой)
            all_docs = Document.objects.exclude(id=document.id)\
                                       .exclude(vector__isnull=True)\
                                       .filter(on_defense=True)
            
            for doc in all_docs:
                # Проверяем кэш схожести
                cached_sim = get_cached_similarity(document.id, doc.id)
                if cached_sim is not None:
                    if cached_sim > self.similarity_threshold:
                        similar_docs.append((doc, cached_sim))
                    continue
                
                # Получаем вектор с кэшированием
                doc_vector = get_cached_vector(doc.id)
                if doc_vector is None:
                    doc_vector = doc.get_vector_array()
                    if doc_vector is not None:
                        cache_vector(doc.id, doc_vector)
                
                if doc_vector is not None:
                    similarity = self._cosine_similarity(current_vector, doc_vector)
                    # Кэшируем результат сравнения
                    cache_similarity_result(document.id, doc.id, similarity)
                    
                    if similarity > self.similarity_threshold:
                        similar_docs.append((doc, similarity))
            
            similar_docs.sort(key=lambda x: x[1], reverse=True)
            
        except Exception as e:
            print(f"Ошибка при поиске похожих документов: {e}")
        
        return similar_docs
    
    def _find_similar_documents_text_based(self, document: Document, document_text: str, max_docs: int = 50) -> List[Tuple[Document, float]]:
        """
        Находит похожие документы на основе текстового анализа (fallback когда векторы недоступны)
        
        Args:
            document: Документ для анализа
            document_text: Текст документа
            max_docs: Максимальное количество документов для проверки (для производительности)
            
        Returns:
            Список кортежей (документ, схожесть)
        """
        similar_docs = []
        
        try:
            # Предобрабатываем текст документа
            document_text_clean = self.preprocess_text(document_text)
            
            # Получаем ограниченное количество документов из общей базы (отправленные на защиту)
            # Документы пользователя также могут быть источниками (сравниваются между собой)
            all_docs = Document.objects.exclude(id=document.id)\
                                       .filter(on_defense=True)\
                                       .filter(txt_file__isnull=False)\
                                       .exclude(txt_file='')[:max_docs]
            
            for doc in all_docs:
                if not doc.txt_file:
                    continue
                
                # Получаем путь к TXT файлу
                try:
                    similar_txt_path = doc.txt_file.path
                except Exception:
                    similar_txt_path = os.path.join(settings.MEDIA_ROOT, str(doc.txt_file))
                
                if not os.path.exists(similar_txt_path):
                    continue
                
                # Читаем текст похожего документа
                try:
                    with open(similar_txt_path, 'r', encoding='utf-8') as f:
                        similar_text = f.read()
                except Exception:
                    continue
                
                # Проверяем длину текста
                if len(similar_text) < self.min_text_length:
                    continue
                
                # Вычисляем схожесть на основе текста
                text_similarity_result = self.calculate_text_similarity(document_text_clean, self.preprocess_text(similar_text))
                similarity = text_similarity_result.get('overall_similarity', 0.0)
                
                # Добавляем документ, если схожесть выше порога
                if similarity > self.similarity_threshold:
                    similar_docs.append((doc, similarity))
            
            # Сортируем по убыванию схожести
            similar_docs.sort(key=lambda x: x[1], reverse=True)
            # Ограничиваем топ-10 для производительности
            similar_docs = similar_docs[:10]
            
        except Exception as e:
            print(f"Ошибка при текстовом поиске похожих документов: {e}")
        
        return similar_docs
