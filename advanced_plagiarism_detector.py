#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Продвинутый скрипт для выявления плагиата текста
Включает множественные алгоритмы сравнения и детальную аналитику
Автор: AI Assistant
Версия: 2.0
"""

import sys
import os
import sqlite3
import hashlib
import numpy as np
import re
from decimal import Decimal
from typing import List, Tuple, Dict, Optional
from collections import Counter

# Добавляем путь к Django проекту
sys.path.append('Folder')

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

import django
django.setup()

from documents.models import Document
from documents import vector
from documents.sim_cos import calculate_originality_large_texts, generate_hashed_shingles, coef_similarity_hashed

class AdvancedPlagiarismDetector:
    """Продвинутый класс для выявления плагиата в текстах"""
    
    def __init__(self):
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
        
        # Удаляем знаки препинания (опционально)
        # text = re.sub(r'[^\w\s]', '', text)
        
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
            
            # Проверяем наличие TXT файла
            if not document.txt_file:
                result['status'] = 'error'
                result['message'] = 'TXT файл не найден'
                return result
            
            txt_path = f"Folder/media/{document.txt_file}"
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
            
            if not similar_docs:
                result['originality'] = 100.0
                result['similarity'] = 0.0
                result['message'] = 'Документ оригинален - похожих документов не найдено'
                result['plagiarism_risk'] = 'very_low'
            else:
                # Детальный анализ с каждым похожим документом
                similarities = []
                similar_texts = []
                detailed_similarities = []
                
                for doc, vector_similarity in similar_docs:
                    if doc.txt_file:
                        similar_txt_path = f"Folder/media/{doc.txt_file}"
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
                    # Рассчитываем оригинальность
                    originality = calculate_originality_large_texts(
                        document_text, 
                        similar_texts, 
                        shingle_size=3
                    )
                    
                    result['originality'] = max(0.0, min(100.0, originality))
                    result['similarity'] = 100 - result['originality']
                    
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
        """Находит похожие документы по косинусному сходству векторов"""
        similar_docs = []
        
        if not document.vector:
            return similar_docs
        
        try:
            current_vector = document.get_vector_array()
            if current_vector is None:
                return similar_docs
            
            all_docs = Document.objects.exclude(id=document.id).exclude(vector__isnull=True)
            
            for doc in all_docs:
                doc_vector = doc.get_vector_array()
                if doc_vector is not None:
                    similarity = self._cosine_similarity(current_vector, doc_vector)
                    if similarity > self.similarity_threshold:
                        similar_docs.append((doc, similarity))
            
            similar_docs.sort(key=lambda x: x[1], reverse=True)
            
        except Exception as e:
            print(f"Ошибка при поиске похожих документов: {e}")
        
        return similar_docs
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Вычисляет косинусное сходство между двумя векторами"""
        try:
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = np.dot(vec1, vec2) / (norm1 * norm2)
            return float(similarity)
        except:
            return 0.0
    
    def generate_detailed_report(self) -> Dict:
        """Генерирует детальный отчет о плагиате"""
        results = []
        
        documents = Document.objects.all().order_by('id')
        
        for doc in documents:
            print(f"Анализируем документ: {doc.name} (ID: {doc.id})")
            result = self.detect_plagiarism(doc.id)
            results.append(result)
            print(f"  Результат: {result['message']}")
            print()
        
        # Статистика
        total_docs = len(results)
        success_docs = [r for r in results if r.get('status') == 'success']
        plagiarized_docs = [r for r in success_docs if r.get('is_plagiarized', False)]
        error_docs = [r for r in results if r.get('status') == 'error']
        warning_docs = [r for r in results if r.get('status') == 'warning']
        
        # Анализ рисков
        risk_levels = {
            'very_high': len([r for r in success_docs if r.get('plagiarism_risk') == 'very_high']),
            'high': len([r for r in success_docs if r.get('plagiarism_risk') == 'high']),
            'medium': len([r for r in success_docs if r.get('plagiarism_risk') == 'medium']),
            'low': len([r for r in success_docs if r.get('plagiarism_risk') == 'low']),
            'very_low': len([r for r in success_docs if r.get('plagiarism_risk') == 'very_low'])
        }
        
        avg_originality = np.mean([r.get('originality', 0) for r in success_docs])
        
        report = {
            'summary': {
                'total_documents': total_docs,
                'successful_analyses': len(success_docs),
                'plagiarized_documents': len(plagiarized_docs),
                'error_documents': len(error_docs),
                'warning_documents': len(warning_docs),
                'average_originality': float(avg_originality),
                'plagiarism_rate': (len(plagiarized_docs) / len(success_docs) * 100) if success_docs else 0
            },
            'risk_analysis': risk_levels,
            'detailed_results': results
        }
        
        return report

def main():
    """Основная функция для запуска продвинутого анализа плагиата"""
    print("=== ПРОДВИНУТАЯ СИСТЕМА ВЫЯВЛЕНИЯ ПЛАГИАТА ===\n")
    
    detector = AdvancedPlagiarismDetector()
    
    # Генерируем детальный отчет
    print("Генерируем детальный отчет...")
    report = detector.generate_detailed_report()
    
    # Выводим сводку
    summary = report['summary']
    print(f"\n=== СВОДНЫЙ ОТЧЕТ ===")
    print(f"Всего документов: {summary['total_documents']}")
    print(f"Успешно проанализировано: {summary['successful_analyses']}")
    print(f"Документов с плагиатом: {summary['plagiarized_documents']}")
    print(f"Документов с ошибками: {summary['error_documents']}")
    print(f"Документов с предупреждениями: {summary['warning_documents']}")
    print(f"Средняя оригинальность: {summary['average_originality']:.2f}%")
    print(f"Процент плагиата: {summary['plagiarism_rate']:.2f}%")
    
    # Анализ рисков
    print(f"\n=== АНАЛИЗ РИСКОВ ===")
    risk_analysis = report['risk_analysis']
    for risk_level, count in risk_analysis.items():
        print(f"{risk_level.replace('_', ' ').title()}: {count} документов")
    
    # Детальные результаты
    print(f"\n=== ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ ===")
    for result in report['detailed_results']:
        if result['status'] == 'success':
            print(f"\n📄 Документ '{result['document_name']}' (ID: {result['document_id']}):")
            print(f"  Оригинальность: {result['originality']:.2f}%")
            print(f"  Схожесть: {result['similarity']:.2f}%")
            print(f"  Риск плагиата: {result['plagiarism_risk'].replace('_', ' ').title()}")
            print(f"  Статус: {'🚨 ПЛАГИАТ' if result['is_plagiarized'] else '✅ ОРИГИНАЛ'}")
            print(f"  Сообщение: {result['message']}")
            
            if result['similar_documents']:
                print(f"  🔍 Похожие документы:")
                for sim_doc in result['similar_documents']:
                    print(f"    - {sim_doc['name']} (ID: {sim_doc['id']})")
                    print(f"      Векторная схожесть: {sim_doc['vector_similarity']:.3f}")
                    print(f"      Текстовая схожесть: {sim_doc['text_similarity']:.3f}")
                    print(f"      Детальная схожесть:")
                    for method, value in sim_doc['detailed_similarity'].items():
                        print(f"        {method}: {value:.3f}")
        elif result['status'] == 'warning':
            print(f"\n⚠️ Предупреждение в документе '{result.get('document_name', 'Unknown')}' (ID: {result['document_id']}): {result['message']}")
        else:
            print(f"\n❌ Ошибка в документе '{result.get('document_name', 'Unknown')}' (ID: {result['document_id']}): {result['message']}")

if __name__ == "__main__":
    main()
