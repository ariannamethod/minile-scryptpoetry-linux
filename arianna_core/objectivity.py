"""
Objectivity - Мини-динамические веса для Mini LE через веб-поиск

Асинхронно ищет контекст в интернете для обогащения ответов Mini LE.
Создает небольшое окно знаний (5-10 строк) для влияния на генерацию.
"""

import asyncio
import aiohttp
import os
import re
import random
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote_plus
import logging

# Настройки для Mini LE
SEARCH_TIMEOUT = 5  # секунд на поиск
MAX_RESULTS = 3     # максимум результатов
CONTEXT_LINES = 8   # строк контекста для Mini LE (меньше чем у LE)
LOG_DIR = Path("datasets")  # куда складывать найденное для дообучения


class ObjectivitySearch:
    """Мини-динамические веса через веб-поиск для Mini LE."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.search_engines = [
            self._search_duckduckgo,
            self._search_wikipedia_api,
            self._search_simple_google
        ]
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=SEARCH_TIMEOUT),
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _search_duckduckgo(self, query: str) -> List[str]:
        """Простой поиск через DuckDuckGo Instant Answer API."""
        try:
            url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []
                    
                    # Абстракт
                    if data.get('Abstract'):
                        results.append(data['Abstract'])
                    
                    # Определение
                    if data.get('Definition'):
                        results.append(data['Definition'])
                    
                    # Связанные темы
                    for topic in data.get('RelatedTopics', [])[:2]:
                        if isinstance(topic, dict) and topic.get('Text'):
                            results.append(topic['Text'])
                    
                    return results[:3]
        except Exception as e:
            logging.debug(f"DuckDuckGo search failed: {e}")
        return []
    
    async def _search_wikipedia_api(self, query: str) -> List[str]:
        """Поиск через Wikipedia API."""
        try:
            # Поиск страниц
            search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(query)}"
            async with self.session.get(search_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('extract'):
                        # Разбиваем на предложения
                        sentences = re.split(r'[.!?]+', data['extract'])
                        return [s.strip() for s in sentences[:3] if s.strip()]
        except Exception as e:
            logging.debug(f"Wikipedia search failed: {e}")
        return []
    
    async def _search_simple_google(self, query: str) -> List[str]:
        """Простой поиск фрагментов (fallback)."""
        # Это заглушка - можно добавить другие источники
        return []
    
    def _extract_key_phrases(self, text_lines: List[str], user_query: str) -> List[str]:
        """Извлекает ключевые фразы из найденного текста."""
        all_text = " ".join(text_lines).lower()
        query_words = set(user_query.lower().split())
        
        # Ищем предложения с ключевыми словами из запроса
        sentences = re.split(r'[.!?]+', all_text)
        relevant_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Минимальная длина
                # Проверяем пересечение с запросом
                sentence_words = set(sentence.split())
                if query_words & sentence_words:  # Есть пересечение
                    relevant_sentences.append(sentence)
        
        return relevant_sentences[:CONTEXT_LINES]
    
    def _calculate_influence_strength(self, context_lines: List[str], user_query: str) -> float:
        """Вычисляет силу влияния найденного контекста (0.0-1.0)."""
        if not context_lines:
            return 0.0
        
        query_words = set(user_query.lower().split())
        total_relevance = 0.0
        
        for line in context_lines:
            line_words = set(line.lower().split())
            # Пересечение слов
            intersection = query_words & line_words
            relevance = len(intersection) / max(len(query_words), 1)
            total_relevance += relevance
        
        # Нормализуем
        avg_relevance = total_relevance / len(context_lines)
        return min(avg_relevance * 2, 1.0)  # Усиливаем влияние
    
    def _select_context_words(self, context_lines: List[str], count: int = 3) -> List[str]:
        """Выбирает интересные слова из контекста для влияния на генерацию."""
        all_words = []
        
        for line in context_lines:
            # Извлекаем существительные и прилагательные (простая эвристика)
            words = re.findall(r'\b[a-zA-Z]{4,}\b', line)
            for word in words:
                word = word.lower()
                # Фильтруем служебные слова
                if word not in {'that', 'this', 'with', 'from', 'they', 'were', 'been', 'have', 'will', 'would', 'could', 'should'}:
                    all_words.append(word)
        
        # Выбираем случайные уникальные слова
        unique_words = list(set(all_words))
        return random.sample(unique_words, min(count, len(unique_words)))
    
    async def search_context(self, user_query: str) -> Dict[str, any]:
        """
        Ищет контекст для запроса пользователя.
        
        Returns:
            {
                'context_lines': List[str],     # Строки контекста
                'influence_strength': float,    # Сила влияния (0.0-1.0)  
                'context_words': List[str],     # Слова для влияния на генерацию
                'found_sources': int            # Количество найденных источников
            }
        """
        if not user_query.strip():
            return {
                'context_lines': [],
                'influence_strength': 0.0,
                'context_words': [],
                'found_sources': 0
            }
        
        all_results = []
        found_sources = 0
        
        # Пробуем разные поисковики
        for search_func in self.search_engines:
            try:
                results = await search_func(user_query)
                if results:
                    all_results.extend(results)
                    found_sources += 1
            except Exception as e:
                logging.debug(f"Search engine failed: {e}")
        
        if not all_results:
            return {
                'context_lines': [],
                'influence_strength': 0.0,
                'context_words': [],
                'found_sources': 0
            }
        
        # Извлекаем ключевые фразы
        context_lines = self._extract_key_phrases(all_results, user_query)
        
        # Вычисляем силу влияния
        influence_strength = self._calculate_influence_strength(context_lines, user_query)
        
        # Выбираем слова для влияния
        context_words = self._select_context_words(context_lines)
        
        logging.info(f"🌐 Objectivity: {len(context_lines)} lines, influence: {influence_strength:.2f}, words: {context_words}")
        
        return {
            'context_lines': context_lines[:CONTEXT_LINES],
            'influence_strength': influence_strength,
            'context_words': context_words,
            'found_sources': found_sources
        }
    
    def log_context_for_training(self, context_lines: List[str], user_query: str) -> None:
        """Сохраняет найденный контекст для дообучения Mini LE."""
        if not context_lines:
            return
        
        LOG_DIR.mkdir(exist_ok=True)
        log_file = LOG_DIR / "objectivity_context.txt"
        
        try:
            with log_file.open("a", encoding="utf-8") as f:
                f.write(f"# Query: {user_query}\n")
                for line in context_lines:
                    if line.strip():
                        f.write(f"{line.strip()}\n")
                f.write("\n")  # Разделитель
        except Exception as e:
            logging.debug(f"Failed to log context: {e}")


# Глобальный экземпляр для переиспользования
_search_instance: Optional[ObjectivitySearch] = None


async def search_objectivity(user_query: str) -> Dict[str, any]:
    """Удобная асинхронная функция для поиска контекста."""
    async with ObjectivitySearch() as searcher:
        result = await searcher.search_context(user_query)
        
        # Логируем для дообучения
        if result['context_lines']:
            searcher.log_context_for_training(result['context_lines'], user_query)
        
        return result


def search_objectivity_sync(user_query: str) -> Dict[str, any]:
    """Синхронная обертка для использования в Mini LE."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Если уже в event loop, создаем новый
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, search_objectivity(user_query))
                return future.result(timeout=SEARCH_TIMEOUT + 2)
        else:
            return asyncio.run(search_objectivity(user_query))
    except Exception as e:
        logging.debug(f"Objectivity search failed: {e}")
    return {
        'context_lines': [],
        'influence_strength': 0.0,
        'context_words': [],
        'found_sources': 0
    }


# Для тестирования
if __name__ == "__main__":
    async def test():
        async with ObjectivitySearch() as searcher:
            queries = [
                "what is consciousness",
                "artificial intelligence",
                "quantum physics",
                "love and meaning"
            ]
            
            for query in queries:
                print(f"\n{'='*50}")
                print(f"Testing query: '{query}'")
                result = await searcher.search_context(query)
                
                print(f"Influence strength: {result['influence_strength']:.2f}")
                print(f"Context words: {result['context_words']}")
                print("Context lines:")
                for i, line in enumerate(result['context_lines'][:5], 1):
                    print(f"  {i}. {line}")
    
    asyncio.run(test())
