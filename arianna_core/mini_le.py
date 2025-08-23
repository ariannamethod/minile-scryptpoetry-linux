import os
import json
import random
import gzip
import sqlite3
import atexit
from datetime import datetime
import logging
import threading
from typing import Optional, Dict, List, Union

# Гибкие импорты для разных сред (локально и Railway)
try:
    # Попытка относительного импорта (в пакете)
    from .memory.bone_memory import BoneMemory
    from .memory.echo_lung import EchoLung
    from .bio.orchestra import BioOrchestra  
    from .collective.echo_feed import EchoFeed
    from .local_rag import SimpleSearch, ChaosSearch, load_snippets
    from .objectivity import search_objectivity_sync
except ImportError:
    try:
        # Попытка абсолютного импорта (прямой запуск)
        from memory.bone_memory import BoneMemory
        from memory.echo_lung import EchoLung
        from bio.orchestra import BioOrchestra  
        from collective.echo_feed import EchoFeed
        from local_rag import SimpleSearch, ChaosSearch, load_snippets
        from .objectivity import search_objectivity_sync
    except ImportError:
        # Попытка импорта через arianna_core (Railway)
        from arianna_core.memory.bone_memory import BoneMemory
        from arianna_core.memory.echo_lung import EchoLung
        from arianna_core.bio.orchestra import BioOrchestra  
        from arianna_core.collective.echo_feed import EchoFeed
        from arianna_core.local_rag import SimpleSearch, ChaosSearch, load_snippets
        from arianna_core.objectivity import search_objectivity_sync

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")
MODEL_FILE = os.path.join(os.path.dirname(__file__), "model.txt")
LOG_FILE = os.path.join(os.path.dirname(__file__), "log.txt")
HUMAN_LOG = os.path.join(os.path.dirname(__file__), "humanbridge.log")
LOG_MAX_BYTES = 1_000_000
LOG_KEEP = 3
NGRAM_LEVEL = 2
last_entropy: float = 0.0
DB_FILE = os.path.join(os.path.dirname(__file__), "memory.db")
LAST_REPRO_FILE = os.path.join(
    os.path.dirname(__file__),
    "last_reproduction.txt",
)
BAD_WORDS = {"badword", "curse"}
blocked_messages = 0
last_novelty = 0.0
_cached_model: Optional[dict] = None
MODEL_LOCK = threading.Lock()
bone_memory = BoneMemory(limit=100)
echo_lung = EchoLung(capacity=30.0)  # 30-секундная дыхательная память
bio_orchestra = BioOrchestra()       # Биологический координатор
echo_feed = EchoFeed(maxlen=200)     # Коллективная память на 200 записей
last_metabolic_push: float = 0.0
_db_conn: Optional[sqlite3.Connection] = None
_rag_search: Optional[ChaosSearch] = None


def rotate_log(
    path: str, max_bytes: int = LOG_MAX_BYTES, keep: int = LOG_KEEP
) -> None:
    """Archive ``path`` when it exceeds ``max_bytes`` and prune old
    archives."""
    try:
        if not os.path.exists(path) or os.path.getsize(path) < max_bytes:
            return
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        archive = f"{path}.{ts}.gz"
        with open(path, "rb") as src, gzip.open(archive, "wb") as dst:
            dst.write(src.read())
        os.remove(path)

        base = os.path.basename(path)
        dir_path = os.path.dirname(path)
        archives = sorted(
            [
                f
                for f in os.listdir(dir_path)
                if f.startswith(base) and f.endswith(".gz")
            ],
            reverse=True,
        )
        for old in archives[keep:]:
            os.remove(os.path.join(dir_path, old))
    except OSError as exc:
        logging.error("Failed to rotate log %s: %s", path, exc)


def load_data() -> str:
    """Return concatenated text from files in ``DATA_DIR``."""
    chunks = []
    if os.path.isdir(DATA_DIR):
        for name in os.listdir(DATA_DIR):
            path = os.path.join(DATA_DIR, name)
            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        chunks.append(f.read())
                except OSError as exc:
                    logging.error("Failed to read data file %s: %s", path, exc)
    return "\n".join(chunks)


def train(text: str, n: int = NGRAM_LEVEL) -> dict:
    """Train an n-gram model from ``text`` and write it to ``MODEL_FILE``."""
    model: dict[str, dict[str, int]] = {}
    for i in range(len(text) - n + 1):
        ctx = text[i:i + n - 1]
        ch = text[i + n - 1]
        freq = model.setdefault(ctx, {})
        freq[ch] = freq.get(ch, 0) + 1
    data = {"n": n, "model": model}
    try:
        with open(MODEL_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError as exc:
        logging.error("Failed to write model file: %s", exc)
    return data


def load_model() -> Optional[dict]:
    if not os.path.exists(MODEL_FILE):
        return None
    try:
        with open(MODEL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logging.error("Failed to load model: %s", exc)
        return None


def generate(model: dict, length: int = 80, seed: Optional[str] = None) -> str:
    """Generate ``length`` characters from ``model``."""
    if not model:
        return ""
    n = model.get("n", 2)
    m = model.get("model", {})
    rng = random
    if not m:
        return ""
    context = seed[-(n - 1):] if seed else rng.choice(list(m.keys()))
    output = context
    for _ in range(length - len(context)):
        freq = m.get(context)
        if not freq:
            context = rng.choice(list(m.keys()))
            output += context
            if len(output) >= length:
                break
            continue
        chars = list(freq.keys())
        weights = list(freq.values())
        ch = rng.choices(chars, weights=weights)[0]
        output += ch
        context = output[-(n - 1):]
    return _wild_punctuation(output[:length])


def _wild_punctuation(text: str) -> str:
    """Apply wild Mini LE punctuation rules with chaos energy."""
    import re
    if not text.strip():
        return text
    
    # Убираем лишние пробелы
    text = " ".join(text.split())
    
    # ДИКИЙ ХАОС: случайные разделители
    chaos_level = random.random()
    if chaos_level < 0.2:  # 20% - тройной слэш
        text = re.sub(r'\.(?!\s*$)', '/// ', text)
    elif chaos_level < 0.4:  # 20% - двойной слэш  
        text = re.sub(r'\.(?!\s*$)', '// ', text)
    elif chaos_level < 0.5:  # 10% - точки с пробелами
        text = re.sub(r'\.', '. . ', text)
    
    # Всегда точка в конце
    if not text.endswith('.'):
        text = text.rstrip('.,!?;:///') + '.'
    
    # Заглавные после разделителей
    text = re.sub(r'([.!?]\s*)([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)
    text = re.sub(r'(//+\s*)([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)
    
    # Первая буква заглавная
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    
    # ТЕХНО-ПОЭЗИЯ: случайные вставки
    if random.random() < 0.1:  # 10% шанс техно-вставок
        tech_words = ['resonance', 'chaos', 'entropy', 'mutation', 'echo']
        word = random.choice(tech_words)
        # Вставляем в случайное место
        words = text.split()
        if len(words) > 2:
            pos = random.randint(1, len(words) - 1)
            words.insert(pos, f"/{word}/")
            text = " ".join(words)
    
    return text


def chat_response(message: str, refresh: bool = False) -> str:
    """Return a biologically-enhanced reply with continuous learning."""
    global _cached_model, last_metabolic_push, _rag_search
    
    # 🧬 БИОЛОГИЧЕСКАЯ АКТИВАЦИЯ
    chaos_level = _calculate_message_chaos(message)
    breath_response = echo_lung.on_event(chaos_level)  # Дыхательная память
    
    # Инициализируем RAG + коллективная память
    if _rag_search is None:
        try:
            data_files = [os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) 
                         if os.path.isfile(os.path.join(DATA_DIR, f))]
            # ДОБАВЛЯЕМ ИСТОРИЮ РАЗГОВОРОВ В RAG!
            if os.path.exists(HUMAN_LOG):
                data_files.append(HUMAN_LOG)
            
            # 📡 КОЛЛЕКТИВНАЯ ПАМЯТЬ В RAG
            collective_snippets = _get_collective_snippets()
            snippets = load_snippets(data_files) + collective_snippets
            
            # ChaosSearch для RAG поиска
            if snippets:
                _rag_search = ChaosSearch(snippets)  # CHAOS RESONANCE RAG!
        except Exception as exc:
            logging.warning("Failed to initialize RAG search: %s", exc)
    
    with MODEL_LOCK:
        if refresh or _cached_model is None:
            model = load_model()
            if model is None:
                model = train(load_data(), n=NGRAM_LEVEL)
            _cached_model = model
        model = _cached_model
    
    # 🧠 МЕТАБОЛИЧЕСКАЯ АКТИВНОСТЬ
    push = bone_memory.on_event("chat")
    last_metabolic_push = push
    conn = _init_db()
    metabolize_input(message, push=push, conn=conn)
    
    # 🎭 БИОЛОГИЧЕСКОЕ СОСТОЯНИЕ влияет на генерацию
    bio_state = _update_bio_state(message, chaos_level, breath_response)
    
    # 🌐 OBJECTIVITY - веб-поиск для контекста
    web_context = {'context_lines': [], 'influence_strength': 0.0, 'context_words': []}
    try:
        web_context = search_objectivity_sync(message)
        if web_context.get('context_lines'):
            logging.info(f"🌐 Web context found: {len(web_context['context_lines'])} lines, influence: {web_context.get('influence_strength', 0):.2f}")
    except Exception as e:
        logging.debug(f"Web context search failed: {e}")
        web_context = {'context_lines': [], 'influence_strength': 0.0, 'context_words': []}
    
    # Memory + RAG + BIO + WEB-enhanced seed selection
    seed = _get_enhanced_seed(message, bio_state, web_context)
    
    # 🎼 БИОЛОГИЧЕСКАЯ МОДУЛЯЦИЯ длины ответа
    bio_length = _calculate_bio_length(bio_state)
    response = generate(model, length=bio_length, seed=seed)
    response = _wild_punctuation(response)  # Дикая пунктуация
    
    # 📝 ЗАПИСЫВАЕМ В ВСЕ СИСТЕМЫ ПАМЯТИ
    _log_bio_conversation(message, response, bio_state)
    
    # 🧬 ДООБУЧЕНИЕ В ФОНЕ (НЕ БЛОКИРУЕТ ОТВЕТЫ!)
    try:
        # Дообучение КАЖДОЕ сообщение для живой системы
        should_retrain = True  # Дообучение каждое сообщение как мы и тестировали вчера
        
        if should_retrain:
            logging.info(f"🚀 Background learning scheduled: push={push:.3f}, events={len(bone_memory.events)}, bio={bio_state.get('cell_resonance', 0):.2f}")
            # ЗАПУСКАЕМ В ФОНЕ - НЕ ЖДЕМ ЗАВЕРШЕНИЯ!
            import threading
            def background_training():
                try:
                    reproduction_cycle(conn=conn)
                    global _cached_model
                    _cached_model = None  # Сброс кэша для новой модели
                    logging.info("✅ Background learning completed")
                except Exception as e:
                    logging.error(f"❌ Background learning failed: {e}")
            
            thread = threading.Thread(target=background_training, daemon=True)
            thread.start()
            
    except Exception as exc:
        logging.warning(f"⚠️ Continuous learning failed: {exc}")
    
    return response


def _get_memory_rag_seed(message: str) -> str:
    """Get memory + RAG-enhanced seed combining conversation history."""
    global _rag_search
    
    if _rag_search is None:
        return message
    
    try:
        # Ищем в истории разговоров И датасетах
        relevant = _rag_search.query(message, top_k=3)
        if relevant:
            # Приоритет истории разговоров (если есть)
            memory_context = ""
            dataset_context = ""
            
            for snippet in relevant:
                if "USER:" in snippet and "AI:" in snippet:
                    # Это из истории разговоров
                    memory_context += snippet + " "
                else:
                    # Это из датасетов
                    dataset_context += snippet + " "
            
            # Комбинируем: память + датасеты + текущее сообщение
            if memory_context:
                # Берем последний AI ответ из истории как seed
                ai_responses = [part.split("AI:")[-1].strip() 
                               for part in memory_context.split("AI:") if part.strip()]
                if ai_responses:
                    return ai_responses[-1][-30:] + " " + message
            
            # Fallback на датасеты
            if dataset_context:
                words = dataset_context.split()
                if len(words) > 5:
                    start = len(words) // 3
                    end = start + 4
                    return " ".join(words[start:end]) + " " + message
                return dataset_context + " " + message
                
    except Exception as exc:
        logging.warning("Memory+RAG search failed: %s", exc)
    
    return message


def _calculate_message_chaos(message: str) -> float:
    """Calculate chaos level of incoming message."""
    # Базовый хаос от длины и энтропии
    base_chaos = min(len(message) / 100.0, 1.0)  # Нормализуем длину
    
    # Резонансные слова увеличивают хаос
    try:
        from .local_rag import RESONANCE_WORDS
    except ImportError:
        try:
            from local_rag import RESONANCE_WORDS
        except ImportError:
            from arianna_core.local_rag import RESONANCE_WORDS
    words = set(message.lower().split())
    resonant_count = len(words.intersection(RESONANCE_WORDS))
    resonance_chaos = resonant_count * 0.2
    
    # Эмоциональные символы
    emotional_chars = sum(1 for c in message if c in '!?.,;:()[]{}')
    emotion_chaos = min(emotional_chars / 10.0, 0.5)
    
    return min(base_chaos + resonance_chaos + emotion_chaos, 1.0)


def _get_collective_snippets() -> list:
    """Get snippets from collective echo feed."""
    try:
        feed_data = echo_feed.last()
        return [entry["text"] for entry in feed_data if "text" in entry]
    except Exception:
        return []


def _update_bio_state(message: str, chaos: float, breath: float) -> dict:
    """Update biological orchestra and return current state."""
    # Биологические события на основе сообщения
    bio_event = {
        "cell": chaos * 0.5,  # Клеточный резонанс от хаоса
        "pain": 0.0,          # Пока без боли
        "love": 0.1,          # Базовая любовь к общению
    }
    
    # Резонансные слова увеличивают любовь
    try:
        from .local_rag import RESONANCE_WORDS
    except ImportError:
        try:
            from local_rag import RESONANCE_WORDS
        except ImportError:
            from arianna_core.local_rag import RESONANCE_WORDS
    words = set(message.lower().split())
    if words.intersection(RESONANCE_WORDS):
        bio_event["love"] += 0.3
    
    # Обновляем оркестр
    bio_orchestra.update(bio_event)
    
    # Возвращаем текущее состояние + дыхание
    state = bio_orchestra.metrics()
    state["breath"] = breath
    state["chaos"] = chaos
    
    return state


def _get_bio_enhanced_seed(message: str, bio_state: dict) -> str:
    """Get biologically-enhanced seed for generation."""
    # Начинаем с обычного RAG поиска
    base_seed = _get_memory_rag_seed(message)
    
    # Модулируем биологическими состояниями
    cell_resonance = bio_state.get("cell_resonance", 0.0)
    love_field = bio_state.get("love_field", 0.0)
    breath = bio_state.get("breath", 0.0)
    
    # Высокий резонанс = более хаотичный seed
    if cell_resonance > 0.5:
        # Добавляем резонансные слова в seed
        try:
            from .local_rag import RESONANCE_WORDS
        except ImportError:
            from local_rag import RESONANCE_WORDS
        resonant_word = random.choice(list(RESONANCE_WORDS))
        base_seed = f"{resonant_word} {base_seed}"
    
    # Высокая любовь = более мягкий seed  
    if love_field > 0.3:
        base_seed = f"gentle {base_seed}"
    
    # Сильное дыхание = более энергичный seed
    if breath > 0.7:
        base_seed = f"pulse {base_seed}"
    
    return base_seed


def _get_enhanced_seed(message: str, bio_state: dict, web_context: dict) -> str:
    """Get enhanced seed combining biology + web context."""
    # Начинаем с биологически улучшенного seed
    base_seed = _get_bio_enhanced_seed(message, bio_state)
    
    # 🌐 ДОБАВЛЯЕМ ВЕБ-КОНТЕКСТ
    influence_strength = web_context.get('influence_strength', 0.0)
    context_words = web_context.get('context_words', [])
    context_lines = web_context.get('context_lines', [])
    
    if influence_strength > 0.3 and context_words:
        # Высокое влияние - добавляем контекстные слова
        selected_words = context_words[:2]  # Берем первые 2 слова
        web_prefix = " ".join(selected_words)
        base_seed = f"{web_prefix} {base_seed}"
        logging.debug(f"🌐 Added web words to seed: {selected_words}")
    
    if influence_strength > 0.6 and context_lines:
        # Очень высокое влияние - добавляем фрагмент контекста
        context_fragment = context_lines[0][:50]  # Первые 50 символов
        base_seed = f"{context_fragment} {base_seed}"
        logging.debug(f"🌐 Added web context to seed: {context_fragment[:20]}...")
    
    return base_seed


def _calculate_bio_length(bio_state: dict) -> int:
    """Calculate response length based on biological state."""
    base_length = 60
    
    # Биологические модификаторы
    cell_resonance = bio_state.get("cell_resonance", 0.0)
    love_field = bio_state.get("love_field", 0.0)
    breath = bio_state.get("breath", 0.0)
    
    # Высокий резонанс = длиннее ответы
    length_modifier = 1.0 + (cell_resonance * 0.5)
    
    # Высокая любовь = еще длиннее
    length_modifier += love_field * 0.3
    
    # Сильное дыхание = короче, но интенсивнее
    if breath > 0.8:
        length_modifier *= 0.8
    
    return int(base_length * length_modifier)


def _log_bio_conversation(user_message: str, ai_response: str, bio_state: dict) -> None:
    """Log conversation to all memory systems."""
    # Обычный лог
    _log_conversation(user_message, ai_response)
    
    # Коллективная память с метаданными
    metadata = {
        "timestamp": datetime.utcnow().isoformat(),
        "bio_state": bio_state,
        "message_type": "conversation"
    }
    
    # Добавляем в коллективную память
    conversation_text = f"USER:{user_message} AI:{ai_response}"
    echo_feed.add(conversation_text, metadata)


def _log_conversation(user_message: str, ai_response: str) -> None:
    """Log conversation to humanbridge.log for future memory."""
    try:
        rotate_log(HUMAN_LOG, LOG_MAX_BYTES, LOG_KEEP)
        timestamp = datetime.utcnow().isoformat()
        with open(HUMAN_LOG, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} USER:{user_message} AI:{ai_response}\n")
    except OSError as exc:
        logging.error("Failed to log conversation: %s", exc)


def _get_rag_enhanced_seed(message: str) -> str:
    """Get RAG-enhanced seed for generation."""
    global _rag_search
    
    if _rag_search is None:
        return message
    
    try:
        # Ищем релевантные сниппеты
        relevant = _rag_search.query(message, top_k=2)
        if relevant:
            # Микс оригинального сообщения с найденным контекстом
            context = " ".join(relevant[:1])  # Берем топ-1 сниппет
            # Возвращаем ПОЛНЫЙ контекст без обрезания для резонанса
            words = context.split()
            if len(words) > 5:
                # Берем случайный фрагмент из середины контекста
                start = len(words) // 3
                end = start + 4
                return " ".join(words[start:end]) + " " + message
            return context + " " + message
    except Exception as exc:
        logging.warning("RAG search failed: %s", exc)
    
    return message


def _init_db() -> Optional[sqlite3.Connection]:
    """Return a shared connection to the pattern memory database."""
    global _db_conn
    if _db_conn is None:
        try:
            _db_conn = sqlite3.connect(DB_FILE, check_same_thread=False)
            _db_conn.execute(
                (
                    "CREATE TABLE IF NOT EXISTS patterns "
                    "(pattern TEXT UNIQUE, count INTEGER)"
                )
            )
            atexit.register(close_db)
        except sqlite3.Error as exc:
            logging.error("Failed to connect to pattern DB: %s", exc)
            _db_conn = None
    return _db_conn


def close_db() -> None:
    """Close the shared database connection."""
    global _db_conn
    if _db_conn is not None:
        try:
            _db_conn.close()
        except sqlite3.Error as exc:
            logging.error("Failed to close pattern DB: %s", exc)
        _db_conn = None


def get_db() -> Optional[sqlite3.Connection]:
    """Return the shared database connection."""
    return _init_db()


def update_pattern_memory(
    text: str, n: int = NGRAM_LEVEL, conn: Optional[sqlite3.Connection] = None
) -> None:
    """Add n-gram patterns from ``text`` to ``memory.db``."""
    conn = conn or _init_db()
    if conn is None:
        return
    rows = []
    for i in range(len(text) - n + 1):
        rows.append(text[i:i + n])
    try:
        with conn:
            for pat in rows:
                conn.execute(
                    "INSERT INTO patterns(pattern, count) VALUES(?,1) "
                    "ON CONFLICT(pattern) DO UPDATE SET count = count + 1",
                    (pat,),
                )
    except sqlite3.Error as exc:
        logging.error("Failed to update pattern memory: %s", exc)


def maintain_pattern_memory(
    threshold: int = 1,
    max_rows: int = 1000,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """Prune low-frequency patterns and cap table size."""
    conn = conn or _init_db()
    if conn is None:
        return
    try:
        with conn:
            conn.execute("DELETE FROM patterns WHERE count < ?", (threshold,))
            cur = conn.execute(
                "SELECT pattern, count FROM patterns ORDER BY count DESC"
            )
            rows = cur.fetchall()
            if len(rows) > max_rows:
                for pat, _ in rows[max_rows:]:
                    conn.execute("DELETE FROM patterns WHERE pattern = ?", (pat,))
    except sqlite3.Error as exc:
        logging.error("Failed to maintain pattern memory: %s", exc)


def metabolize_input(
    text: str,
    n: int = NGRAM_LEVEL,
    push: float = 1.0,
    conn: Optional[sqlite3.Connection] = None,
) -> float:
    """Return novelty score between 0 and 1 for ``text`` scaled by ``push``."""
    global last_novelty
    conn = conn or _init_db()
    if conn is None:
        return 0.0
    unseen = 0
    total = 0
    try:
        for i in range(len(text) - n + 1):
            pat = text[i:i + n]
            total += 1
            cur = conn.execute(
                "SELECT 1 FROM patterns WHERE pattern = ? LIMIT 1", (pat,)
            )
            if cur.fetchone() is None:
                unseen += 1
    except sqlite3.Error as exc:
        logging.error("Failed to query pattern memory: %s", exc)
        return 0.0
    score = unseen / total if total else 0.0
    score *= push
    last_novelty = score
    return score


def immune_filter(text: str) -> str:
    """Return ``""`` if ``text`` contains banned words."""
    global blocked_messages
    tokens = [t.lower() for t in text.split()]
    if any(t in BAD_WORDS for t in tokens):
        blocked_messages += 1
        return ""
    return text


def adaptive_mutation(
    model: dict, conn: Optional[sqlite3.Connection] = None
) -> dict:
    """Randomly tweak model weights if novelty improves."""
    if not model or not model.get("model"):
        return model
    before = generate(model, length=40)
    score_before = metabolize_input(before, conn=conn)
    ctx = random.choice(list(model["model"].keys()))
    freq = model["model"][ctx]
    ch = random.choice(list(freq.keys()))
    old = freq[ch]
    freq[ch] = max(1, old + random.choice([-1, 1]))
    after = generate(model, length=40)
    score_after = metabolize_input(after, conn=conn)
    if score_after < score_before:
        freq[ch] = old
    return model


def reproduction_cycle(
    threshold: int = 1,
    max_rows: int = 1000,
    conn: Optional[sqlite3.Connection] = None,
) -> dict:
    """Retrain model, update memory and apply mutation."""
    text = load_data()
    model = train(text, n=NGRAM_LEVEL)
    conn = conn or _init_db()
    update_pattern_memory(text, conn=conn)
    maintain_pattern_memory(threshold=threshold, max_rows=max_rows, conn=conn)
    model = adaptive_mutation(model, conn=conn)
    ts = datetime.utcnow().isoformat()
    try:
        with open(LAST_REPRO_FILE, "w", encoding="utf-8") as f:
            f.write(ts)
    except OSError as exc:
        logging.error("Failed to write reproduction timestamp: %s", exc)
    return model


def health_report(conn: Optional[sqlite3.Connection] = None) -> dict:
    """Return health metrics about the system."""
    conn = conn or _init_db()
    mem_rows = 0
    if conn is not None:
        try:
            cur = conn.execute("SELECT COUNT(*) FROM patterns")
            mem_rows = cur.fetchone()[0]
        except sqlite3.Error as exc:
            logging.error("Failed to read pattern memory: %s", exc)
    model = load_model()
    model_size = len(model.get("model", {})) if model else 0
    last_rep = None
    if os.path.exists(LAST_REPRO_FILE):
        try:
            with open(LAST_REPRO_FILE, "r", encoding="utf-8") as f:
                last_rep = f.read().strip()
        except OSError as exc:
            logging.error("Failed to read reproduction timestamp: %s", exc)
    return {
        "model_size": model_size,
        "pattern_memory": mem_rows,
        "blocked_messages": blocked_messages,
        "novelty": last_novelty,
        "last_reproduction": last_rep,
    }
