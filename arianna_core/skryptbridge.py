"""
SkryptBridge - Основная логика системы (MiniLE + Skryptpoetry)
Отделено от Telegram интерфейса для модульности.
"""
import os
import sys
import asyncio
import logging

# Добавляем пути для импортов (skryptbridge теперь в arianna_core)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'skryptpoetry'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'skryptpoetry', 'arianna_linux'))

# Импорты MiniLE
try:
    from . import mini_le
except ImportError:
    # Fallback для прямого запуска
    import mini_le

# Импорты Skryptpoetry
try:
    from symphony import Symphony
    from letsgo import run_script
    SKRYPTPOETRY_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Skryptpoetry not available: {e}")
    SKRYPTPOETRY_AVAILABLE = False

# Глобальная Symphony - инициализируем сразу
_symphony = None
if SKRYPTPOETRY_AVAILABLE:
    try:
        scripts_path = os.path.join(os.path.dirname(__file__), '..', 'skryptpoetry', 'tongue', 'prelanguage.md')
        dataset_path = os.path.join(os.path.dirname(__file__), '..', 'skryptpoetry', 'datasets', 'dataset01.md')
        _symphony = Symphony(dataset_path=dataset_path, scripts_path=scripts_path)
        logging.info("✅ Symphony initialized at import")
    except Exception as e:
        logging.error(f"❌ Symphony initialization failed: {e}")

def _get_symphony():
    """Возвращает готовую Symphony."""
    return _symphony

async def process_message(message: str) -> str:
    """
    Основная функция обработки сообщений.
    Возвращает ответ MiniLE + визуализация Skryptpoetry.
    """
    try:
        # 1. Получаем ответ от MiniLE
        if hasattr(asyncio, "to_thread"):
            minile_reply = await asyncio.to_thread(mini_le.chat_response, message)
        else:  # Python 3.8 fallback
            loop = asyncio.get_running_loop()
            minile_reply = await loop.run_in_executor(None, mini_le.chat_response, message)
        
        # 2. Добавляем Skryptpoetry визуализацию
        symphony = _get_symphony()
        if SKRYPTPOETRY_AVAILABLE and symphony:
            try:
                # Получаем скрипт на основе ответа MiniLE
                if hasattr(asyncio, "to_thread"):
                    script_code = await asyncio.to_thread(symphony.respond, minile_reply)
                    script_result = await asyncio.to_thread(run_script, script_code)
                else:
                    loop = asyncio.get_running_loop()
                    script_code = await loop.run_in_executor(None, symphony.respond, minile_reply)
                    script_result = await loop.run_in_executor(None, run_script, script_code)
                
                # Комбинируем ответы
                return f"{minile_reply}\n\n{script_result}"
            except Exception as e:
                logging.debug(f"Skryptpoetry visualization failed: {e}")
                return minile_reply
        else:
            return minile_reply
            
    except Exception as e:
        logging.error(f"Message processing failed: {e}")
        return "Error: failed to generate response."

def process_message_sync(message: str) -> str:
    """Синхронная версия для не-async интерфейсов."""
    try:
        # MiniLE ответ
        minile_reply = mini_le.chat_response(message)
        
        # Skryptpoetry визуализация
        symphony = _get_symphony()
        if SKRYPTPOETRY_AVAILABLE and symphony:
            try:
                script_code = symphony.respond(minile_reply)
                script_result = run_script(script_code)
                return f"{minile_reply}\n\n{script_result}"
            except Exception:
                return minile_reply
        else:
            return minile_reply
            
    except Exception as e:
        logging.error(f"Sync message processing failed: {e}")
        return "Error: failed to generate response."

if __name__ == "__main__":
    # Тест системы
    import time
    
    print("=== ТЕСТ SKRYPTBRIDGE ===")
    
    start = time.time()
    response = process_message_sync("hello test")
    print(f"⚡ Время обработки: {time.time() - start:.3f}s")
    print(f"📝 Ответ: {response}")
