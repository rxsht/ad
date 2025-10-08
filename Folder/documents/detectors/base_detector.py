"""
Базовый абстрактный класс для детекторов плагиата
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
import numpy as np


class BasePlagiarismDetector(ABC):
    """Абстрактный базовый класс для всех детекторов плагиата"""
    
    def __init__(self):
        self.similarity_threshold = 0.7
        self.originality_threshold = 80.0
    
    @abstractmethod
    def detect_plagiarism(self, document_id: int) -> Dict:
        """
        Выявляет плагиат для конкретного документа
        
        Args:
            document_id: ID документа в базе данных
            
        Returns:
            Словарь с результатами анализа
        """
        pass
    
    @abstractmethod
    def _find_similar_documents(self, document) -> List[Tuple]:
        """
        Находит похожие документы
        
        Args:
            document: Объект Document
            
        Returns:
            Список кортежей (документ, схожесть)
        """
        pass
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Вычисляет косинусное сходство между двумя векторами"""
        try:
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = np.dot(vec1, vec2) / (norm1 * norm2)
            return float(similarity)
        except Exception:
            return 0.0
