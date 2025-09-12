#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Полностью рабочий скрипт для выявления плагиата текста
Автор: AI Assistant
Версия: 1.0
"""

import sys
import os
import sqlite3
import hashlib
import numpy as np
from decimal import Decimal
from typing import List, Tuple, Dict, Optional

# Добавляем путь к Django проекту
sys.path.append('Folder')

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

import django
django.setup()

from documents.models import Document
from documents import vector
from documents.sim_cos import calculate_originality_large_texts, generate_hashed_shingles, coef_similarity_hashed

class PlagiarismDetector:
    """Класс для выявления плагиата в текстах"""
    
    def __init__(self):
        self.shingle_size = 3  # Размер шинглов для сравнения
        self.similarity_threshold = 0.7  # Порог схожести для векторов
        self.originality_threshold = 80.0  # Порог оригинальности (ниже = подозрительно)
    
    def detect_plagiarism(self, document_id: int) -> Dict:
        """
        Выявляет плагиат для конкретного документа
        
        Args:
            document_id: ID документа в базе данных
            
        Returns:
            Словарь с результатами анализа
        """
        try:
            # Получаем документ
            document = Document.objects.get(id=document_id)
            
            result = {
                'document_id': document_id,
                'document_name': document.name,
                'originality': 0.0,
                'similarity': 0.0,
                'similar_documents': [],
                'is_plagiarized': False,
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
            
            # Находим похожие документы по векторам
            similar_docs = self._find_similar_documents(document)
            
            if not similar_docs:
                # Если нет похожих документов, считаем оригинальным
                result['originality'] = 100.0
                result['similarity'] = 0.0
                result['message'] = 'Документ оригинален - похожих документов не найдено'
            else:
                # Рассчитываем оригинальность
                similar_texts = []
                for doc, similarity in similar_docs:
                    if doc.txt_file:
                        similar_txt_path = f"Folder/media/{doc.txt_file}"
                        if os.path.exists(similar_txt_path):
                            with open(similar_txt_path, 'r', encoding='utf-8') as f:
                                similar_texts.append(f.read())
                
                if similar_texts:
                    originality = calculate_originality_large_texts(
                        document_text, 
                        similar_texts, 
                        shingle_size=self.shingle_size
                    )
                    
                    result['originality'] = max(0.0, min(100.0, originality))
                    result['similarity'] = 100 - result['originality']
                    
                    # Добавляем информацию о похожих документах
                    for doc, similarity in similar_docs:
                        result['similar_documents'].append({
                            'id': doc.id,
                            'name': doc.name,
                            'similarity': float(similarity),
                            'originality': float(doc.result) if doc.result else 0.0
                        })
                    
                    # Определяем, является ли документ плагиатом
                    result['is_plagiarized'] = result['originality'] < self.originality_threshold
                    
                    if result['is_plagiarized']:
                        result['message'] = f'ВНИМАНИЕ: Документ может содержать плагиат! Оригинальность: {result["originality"]:.2f}%'
                    else:
                        result['message'] = f'Документ оригинален. Оригинальность: {result["originality"]:.2f}%'
                else:
                    result['originality'] = 100.0
                    result['similarity'] = 0.0
                    result['message'] = 'Документ оригинален - не удалось прочитать похожие документы'
            
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
            
            # Получаем все остальные документы с векторами
            all_docs = Document.objects.exclude(id=document.id).exclude(vector__isnull=True)
            
            for doc in all_docs:
                doc_vector = doc.get_vector_array()
                if doc_vector is not None:
                    similarity = self._cosine_similarity(current_vector, doc_vector)
                    if similarity > self.similarity_threshold:
                        similar_docs.append((doc, similarity))
            
            # Сортируем по убыванию схожести
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
    
    def analyze_all_documents(self) -> List[Dict]:
        """Анализирует все документы в базе данных"""
        results = []
        
        documents = Document.objects.all().order_by('id')
        
        for doc in documents:
            print(f"Анализируем документ: {doc.name} (ID: {doc.id})")
            result = self.detect_plagiarism(doc.id)
            results.append(result)
            print(f"  Результат: {result['message']}")
            print()
        
        return results
    
    def get_plagiarism_report(self) -> Dict:
        """Генерирует отчет о плагиате для всех документов"""
        results = self.analyze_all_documents()
        
        total_docs = len(results)
        plagiarized_docs = [r for r in results if r.get('is_plagiarized', False)]
        error_docs = [r for r in results if r.get('status') == 'error']
        
        avg_originality = np.mean([r.get('originality', 0) for r in results if r.get('status') == 'success'])
        
        report = {
            'total_documents': total_docs,
            'plagiarized_documents': len(plagiarized_docs),
            'error_documents': len(error_docs),
            'average_originality': float(avg_originality),
            'plagiarism_rate': (len(plagiarized_docs) / total_docs * 100) if total_docs > 0 else 0,
            'results': results
        }
        
        return report

def main():
    """Основная функция для тестирования системы выявления плагиата"""
    print("=== СИСТЕМА ВЫЯВЛЕНИЯ ПЛАГИАТА ===\n")
    
    detector = PlagiarismDetector()
    
    # Анализируем все документы
    print("Анализируем все документы...")
    report = detector.get_plagiarism_report()
    
    print(f"\n=== ОТЧЕТ О ПЛАГИАТЕ ===")
    print(f"Всего документов: {report['total_documents']}")
    print(f"Документов с плагиатом: {report['plagiarized_documents']}")
    print(f"Документов с ошибками: {report['error_documents']}")
    print(f"Средняя оригинальность: {report['average_originality']:.2f}%")
    print(f"Процент плагиата: {report['plagiarism_rate']:.2f}%")
    
    print(f"\n=== ДЕТАЛЬНЫЕ РЕЗУЛЬТАТЫ ===")
    for result in report['results']:
        if result['status'] == 'success':
            print(f"Документ '{result['document_name']}' (ID: {result['document_id']}):")
            print(f"  Оригинальность: {result['originality']:.2f}%")
            print(f"  Схожесть: {result['similarity']:.2f}%")
            print(f"  Статус: {'ПЛАГИАТ' if result['is_plagiarized'] else 'ОРИГИНАЛ'}")
            print(f"  Сообщение: {result['message']}")
            
            if result['similar_documents']:
                print(f"  Похожие документы:")
                for sim_doc in result['similar_documents']:
                    print(f"    - {sim_doc['name']} (ID: {sim_doc['id']}, схожесть: {sim_doc['similarity']:.3f})")
            print()
        else:
            print(f"Ошибка в документе '{result['document_name']}' (ID: {result['document_id']}): {result['message']}")

if __name__ == "__main__":
    main()
