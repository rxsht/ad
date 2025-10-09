"""
Утилиты для кэширования векторов и результатов в Redis
"""

import os
import json
import redis
from django.conf import settings
from typing import Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Подключение к Redis с проверкой доступности
redis_client = None
redis_available = None

def get_redis_client():
    """Получить Redis клиент с проверкой доступности (один раз)"""
    global redis_client, redis_available
    
    if redis_available is False:
        return None
    
    if redis_client is None:
        try:
            # Парсим CELERY_BROKER_URL или используем defaults
            broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
            # Простой парсинг redis://host:port/db
            import re
            match = re.match(r'redis://([^:]+):(\d+)/(\d+)', broker_url)
            if match:
                host, port, db = match.groups()
            else:
                host, port, db = 'localhost', '6379', '0'
            
            redis_client = redis.Redis(
                host=host,
                port=int(port),
                db=int(db),
                decode_responses=False,
                socket_connect_timeout=1,
                socket_timeout=1
            )
            # Проверяем подключение
            redis_client.ping()
            redis_available = True
            logger.info("Redis подключен успешно")
        except Exception as e:
            redis_available = False
            redis_client = None
            logger.warning(f"Redis недоступен, кэширование отключено: {e}")
    
    return redis_client


def get_cached_vector(document_id: int) -> Optional[np.ndarray]:
    """
    Получить вектор документа из кэша
    
    Args:
        document_id: ID документа
        
    Returns:
        numpy array или None
    """
    client = get_redis_client()
    if not client:
        return None
    
    try:
        key = f'vector:{document_id}'
        cached = client.get(key)
        
        if cached:
            vector_data = json.loads(cached)
            return np.array(vector_data)
        
        return None
        
    except Exception:
        return None


def cache_vector(document_id: int, vector: np.ndarray, ttl: int = 3600):
    """
    Сохранить вектор документа в кэш
    
    Args:
        document_id: ID документа
        vector: numpy array вектора
        ttl: время жизни в секундах (по умолчанию 1 час)
    """
    client = get_redis_client()
    if not client:
        return
    
    try:
        key = f'vector:{document_id}'
        vector_json = json.dumps(vector.tolist())
        client.setex(key, ttl, vector_json)
    except Exception:
        pass


def invalidate_vector_cache(document_id: int):
    """
    Инвалидировать кэш вектора документа
    
    Args:
        document_id: ID документа
    """
    client = get_redis_client()
    if not client:
        return
    
    try:
        key = f'vector:{document_id}'
        client.delete(key)
    except Exception:
        pass


def cache_similarity_result(doc1_id: int, doc2_id: int, similarity: float, ttl: int = 7200):
    """
    Кэшировать результат сравнения двух документов
    
    Args:
        doc1_id, doc2_id: ID документов
        similarity: значение схожести
        ttl: время жизни (по умолчанию 2 часа)
    """
    client = get_redis_client()
    if not client:
        return
    
    try:
        key = f'similarity:{min(doc1_id, doc2_id)}:{max(doc1_id, doc2_id)}'
        client.setex(key, ttl, str(similarity))
    except Exception:
        pass


def get_cached_similarity(doc1_id: int, doc2_id: int) -> Optional[float]:
    """
    Получить кэшированный результат сравнения
    
    Args:
        doc1_id, doc2_id: ID документов
        
    Returns:
        float значение схожести или None
    """
    client = get_redis_client()
    if not client:
        return None
    
    try:
        key = f'similarity:{min(doc1_id, doc2_id)}:{max(doc1_id, doc2_id)}'
        cached = client.get(key)
        
        if cached:
            return float(cached)
        
        return None
    except Exception:
        return None
