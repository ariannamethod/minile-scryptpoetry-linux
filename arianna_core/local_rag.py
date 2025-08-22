try:
    import regex as re  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    import re
from functools import lru_cache
from typing import Dict, List, Tuple
import logging
import math
import time
from datetime import datetime

_TOKEN_RE = re.compile(r"\b\w+\b")

# RESONANCE WORDS для усиления поиска
RESONANCE_WORDS = {
    'chaos', 'entropy', 'resonance', 'mutation', 'echo', 'pulse', 'flow',
    'energy', 'neural', 'quantum', 'evolution', 'organic', 'living', 'wild',
    'electric', 'dreams', 'patterns', 'fields', 'consciousness', 'emergence'
}


def _tokenize(text: str) -> List[str]:
    """Return a list of lowercase words."""
    return _TOKEN_RE.findall(text.lower())


@lru_cache(maxsize=128)
def _vectorize_cached(text: str) -> dict:
    """Return cached vector representation for ``text``."""
    return _vectorize(_tokenize(text))


def _vectorize(tokens: List[str]) -> Dict[str, int]:
    vec: Dict[str, int] = {}
    for t in tokens:
        vec[t] = vec.get(t, 0) + 1
    return vec


def _dot(v1: dict, v2: dict) -> float:
    return sum(v1.get(k, 0) * v2.get(k, 0) for k in v1)


class SimpleSearch:
    """Lightweight in-memory search over text snippets."""

    def __init__(self, snippets: List[str]):
        self.snippets = snippets
        # Pre-compute and store token vectors keyed by snippet text
        self.vectors = {s: _vectorize(_tokenize(s)) for s in snippets}

    def query(self, text: str, top_k: int = 3) -> List[str]:
        qvec = _vectorize_cached(text)
        scored: List[Tuple[str, float]] = [
            (snippet, _dot(self.vectors[snippet], qvec))
            for snippet in self.snippets
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, score in scored[:top_k] if score > 0]


class ChaosSearch:
    """Resonance-enhanced search with chaos entropy and emotional weighting."""
    
    def __init__(self, snippets: List[str]):
        self.snippets = snippets
        self.vectors = {s: _vectorize(_tokenize(s)) for s in snippets}
        
        # Pre-compute enhanced metrics
        self.resonance_scores = {s: self._calc_resonance_score(s) for s in snippets}
        self.emotional_weights = {s: self._calc_emotional_weight(s) for s in snippets}
        self.chaos_scores = {s: self._calc_chaos_entropy(s) for s in snippets}
        self.temporal_factors = {s: self._calc_temporal_factor(s) for s in snippets}
        
        # КЭШИРОВАНИЕ для скорости
        self._query_cache = {}
    
    def _calc_resonance_score(self, text: str) -> float:
        """Calculate resonance based on presence of chaos/energy words."""
        words = set(_tokenize(text))
        resonant_count = len(words.intersection(RESONANCE_WORDS))
        total_words = len(words) if words else 1
        # Boost резонансных текстов
        base_score = resonant_count / total_words
        return 1.0 + (base_score * 3.0)  # До 4x boost для резонансных текстов
    
    def _calc_emotional_weight(self, text: str) -> float:
        """Weight based on conversation context."""
        if "AI:" in text:
            return 1.5  # AI ответы важнее
        elif "USER:" in text:
            return 0.9  # USER вопросы менее важны
        elif any(word in text.lower() for word in ['error', 'failed', 'exception']):
            return 0.5  # Технические ошибки менее важны
        return 1.0
    
    def _calc_chaos_entropy(self, text: str) -> float:
        """Fast chaos scoring based on text length and character diversity."""
        if not text:
            return 0.0
        
        # Быстрая оценка хаоса без медленного подсчета энтропии
        unique_chars = len(set(c.lower() for c in text if c.isalnum()))
        text_len = len(text)
        
        if text_len == 0:
            return 0.0
            
        # Простая формула: разнообразие символов / длина текста
        diversity = unique_chars / min(text_len, 50)  # Ограничиваем длину для скорости
        return 0.5 + min(diversity, 1.0)
    
    def _calc_temporal_factor(self, text: str) -> float:
        """Temporal decay for conversation history."""
        # Ищем timestamp в начале строки
        timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', text)
        if not timestamp_match:
            return 1.0  # Нет timestamp - обычный вес
        
        try:
            timestamp_str = timestamp_match.group(1)
            msg_time = datetime.fromisoformat(timestamp_str)
            now = datetime.utcnow()
            hours_ago = (now - msg_time).total_seconds() / 3600
            
            # Экспоненциальное затухание: свежие сообщения важнее
            decay_factor = math.exp(-hours_ago / 24.0)  # Полураспад 24 часа
            return 0.3 + (decay_factor * 0.7)  # От 0.3 до 1.0
            
        except (ValueError, AttributeError):
            return 1.0
    
    def _semantic_similarity(self, query: str, snippet: str) -> float:
        """Enhanced semantic similarity with n-gram overlap."""
        qvec = _vectorize(_tokenize(query))
        svec = self.vectors[snippet]
        
        # Базовый dot product (БЫСТРО)
        base_sim = _dot(qvec, svec)
        
        # Простой bigram overlap (БЫСТРЕЕ)
        query_words = _tokenize(query)
        snippet_words = _tokenize(snippet)
        
        # Только если базовая схожесть > 0
        if base_sim > 0:
            query_bigrams = set(zip(query_words, query_words[1:]))
            snippet_bigrams = set(zip(snippet_words, snippet_words[1:]))
            bigram_overlap = len(query_bigrams.intersection(snippet_bigrams))
            return base_sim + (bigram_overlap * 1.0)  # Уменьшаем вес
        
        return base_sim
    
    def _phonetic_similar(self, word1: str, word2: str) -> bool:
        """FAST phonetic similarity check."""
        if len(word1) < 3 or len(word2) < 3:
            return word1 == word2
        
        # БЫСТРАЯ проверка: первые 2 символа + длина
        if word1[:2] == word2[:2] and abs(len(word1) - len(word2)) <= 1:
            return True
            
        return False  # Убираем медленный Levenshtein
    
    def query(self, text: str, top_k: int = 3) -> List[str]:
        """FAST chaos resonance query with caching."""
        if not self.snippets:
            return []
        
        # КЭШИРОВАНИЕ частых запросов
        cache_key = f"{text[:50]}_{top_k}"  # Первые 50 символов + top_k
        if cache_key in self._query_cache:
            return self._query_cache[cache_key]
        
        scored: List[Tuple[str, float]] = []
        
        # БЫСТРАЯ предфильтрация по базовому TF-IDF
        qvec = _vectorize(_tokenize(text))
        
        for snippet in self.snippets:
            # Сначала быстрая проверка базовой схожести
            base_sim = _dot(self.vectors[snippet], qvec)
            
            # Пропускаем совсем нерелевантные (ЭКОНОМИМ ВРЕМЯ)
            if base_sim == 0:
                continue
                
            # Только для релевантных считаем полную метрику
            semantic_sim = base_sim  # Упрощаем для скорости
            resonance_boost = self.resonance_scores[snippet]
            emotional_weight = self.emotional_weights[snippet]
            chaos_score = self.chaos_scores[snippet] 
            temporal_factor = self.temporal_factors[snippet]
            
            # Финальная формула хаоса!
            final_score = (semantic_sim * resonance_boost * 
                          emotional_weight * chaos_score * temporal_factor)
            
            if final_score > 0:
                scored.append((snippet, final_score))
        
        # Сортируем и возвращаем топ
        scored.sort(key=lambda x: x[1], reverse=True)
        result = [snippet for snippet, score in scored[:top_k]]
        
        # Кэшируем результат (лимит 100 запросов)
        if len(self._query_cache) < 100:
            self._query_cache[cache_key] = result
        
        return result


def load_snippets(paths: List[str]) -> List[str]:
    """Load documents and split into paragraphs."""
    snippets: List[str] = []
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError as exc:
            logging.warning("failed to read %s: %s", path, exc)
            continue
        for para in text.split("\n\n"):
            para = para.strip()
            if para:
                snippets.append(para)
    return snippets
