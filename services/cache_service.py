import redis
import json
import hashlib
import os
from datetime import timedelta

class RedisCacheService:
    """Сервис для кэширования с использованием Redis."""
    
    def __init__(self):
        """Инициализация подключения к Redis."""
        redis_host = os.environ.get('REDIS_HOST', '176.108.250.9')
        redis_port = int(os.environ.get('REDIS_PORT', 6379))
        redis_db = int(os.environ.get('REDIS_DB', 0))
        redis_password = os.environ.get('REDIS_PASSWORD', None)
        
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=False  # Будем хранить бинарные данные (изображения)
        )
        
        # Время жизни кэша в секундах (по умолчанию 1 день)
        self.cache_ttl = int(os.environ.get('REDIS_CACHE_TTL', 86400))
    
    def _generate_key(self, diagram_type, description):
        """
        Генерирует уникальный ключ для кэша на основе типа диаграммы и описания.
        
        Args:
            diagram_type (str): Тип диаграммы
            description (str): Описание диаграммы
            
        Returns:
            str: Ключ для кэша
        """
        # Создаем составной ключ и хэшируем его для уникальности
        key_data = f"{diagram_type}:{description}"
        return f"diagram_cache:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def get_cached_image(self, diagram_type, description):
        key = self._generate_key(diagram_type, description)
        print(key)
        
        cached_data = self.redis_client.get(key)
        print(cached_data)
        if cached_data:
            image_path = cached_data.decode('utf-8')
            return image_path
        
        return None
    
    def cache_image(self, diagram_type, description, image_data, metadata=None):
        key = self._generate_key(diagram_type, description)
        
        # Сохраняем изображение с указанным временем жизни
        self.redis_client.setex(
            key, 
            timedelta(seconds=self.cache_ttl), 
            image_data
        )
        
        # Если есть метаданные, сохраняем их отдельно
        if metadata:
            metadata_key = f"{key}:metadata"
            self.redis_client.setex(
                metadata_key,
                timedelta(seconds=self.cache_ttl),
                json.dumps(metadata)
            )
        
        return True
    
    def invalidate_cache(self, diagram_type, description):
        """
        Инвалидирует (удаляет) кэш для указанной диаграммы.
        
        Args:
            diagram_type (str): Тип диаграммы
            description (str): Описание диаграммы
            
        Returns:
            bool: True, если кэш был удален
        """
        key = self._generate_key(diagram_type, description)
        metadata_key = f"{key}:metadata"
        
        # Удаляем как само изображение, так и метаданные
        self.redis_client.delete(key)
        self.redis_client.delete(metadata_key)
        
        return True