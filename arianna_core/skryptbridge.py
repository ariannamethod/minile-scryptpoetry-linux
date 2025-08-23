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

# Импорты Skryptpoetry - ТОЛЬКО при первом использовании
SKRYPTPOETRY_AVAILABLE = None  # Ленивая проверка

def _check_skryptpoetry():
    global SKRYPTPOETRY_AVAILABLE
    if SKRYPTPOETRY_AVAILABLE is None:
        try:
            from symphony import Symphony
            from letsgo import run_script
            SKRYPTPOETRY_AVAILABLE = True
            return True
        except ImportError as e:
            logging.warning(f"Skryptpoetry not available: {e}")
            SKRYPTPOETRY_AVAILABLE = False
            return False
    return SKRYPTPOETRY_AVAILABLE

# Ленивая инициализация Symphony - НЕ при импорте
_symphony = None

def _get_symphony():
    """Создает Symphony только при первом обращении."""
    global _symphony
    if _symphony is None and _check_skryptpoetry():
        try:
            # Импортируем ТОЛЬКО при первом использовании
            from symphony import Symphony
            
            scripts_path = os.path.join(os.path.dirname(__file__), '..', 'skryptpoetry', 'tongue', 'prelanguage.md')
            dataset_path = os.path.join(os.path.dirname(__file__), '..', 'skryptpoetry', 'datasets', 'dataset01.md')
            _symphony = Symphony(dataset_path=dataset_path, scripts_path=scripts_path)
            logging.info("✅ Symphony initialized lazily")
        except Exception as e:
            logging.error(f"❌ Symphony initialization failed: {e}")
    return _symphony

async def process_message(message: str) -> str:
    """
    Основная функция обработки сообщений.
    Возвращает ответ MiniLE + визуализация Skryptpoetry.
    """
    try:
        # ЗАПУСКАЕМ MiniLE И Symphony ПАРАЛЛЕЛЬНО
        symphony = _get_symphony()
        
        if hasattr(asyncio, "to_thread"):
            # Параллельный запуск
            minile_task = asyncio.to_thread(mini_le.chat_response, message)
            
            if SKRYPTPOETRY_AVAILABLE and symphony:
                # Symphony работает с message, а не с ответом MiniLE
                script_task = asyncio.to_thread(symphony.respond, message)
                
                # Ждем оба результата
                minile_reply, script_code = await asyncio.gather(minile_task, script_task)
                
                # Выполняем скрипт
                script_result = await asyncio.to_thread(run_script, script_code)
                return f"{minile_reply}\n\n{script_result}"
            else:
                minile_reply = await minile_task
                return minile_reply
        else:
            # Python 3.8 fallback - тоже параллельно
            loop = asyncio.get_running_loop()
            minile_task = loop.run_in_executor(None, mini_le.chat_response, message)
            
            if SKRYPTPOETRY_AVAILABLE and symphony:
                script_task = loop.run_in_executor(None, symphony.respond, message)
                minile_reply, script_code = await asyncio.gather(minile_task, script_task)
                script_result = await loop.run_in_executor(None, run_script, script_code)
                return f"{minile_reply}\n\n{script_result}"
            else:
                minile_reply = await minile_task
                return minile_reply
            
    except Exception as e:
        logging.error(f"Message processing failed: {e}")
        return "Error: failed to generate response."

def process_message_sync(message: str) -> str:
    """Синхронная версия для не-async интерфейсов."""
    try:
        # ПАРАЛЛЕЛЬНОЕ ВЫПОЛНЕНИЕ ДАЖЕ В СИНХРОННОЙ ВЕРСИИ
        import threading
        import queue
        
        results = queue.Queue()
        
        def minile_worker():
            try:
                result = mini_le.chat_response(message)
                results.put(('minile', result))
            except Exception as e:
                results.put(('minile_error', str(e)))
        
        def symphony_worker():
            try:
                symphony = _get_symphony()
                if _check_skryptpoetry() and symphony:
                    # Импортируем run_script только при использовании
                    from letsgo import run_script
                    
                    script_code = symphony.respond(message)  # Работает с исходным сообщением
                    script_result = run_script(script_code)
                    results.put(('symphony', script_result))
                else:
                    results.put(('symphony', ''))
            except Exception:
                results.put(('symphony', ''))
        
        # Запускаем параллельно
        t1 = threading.Thread(target=minile_worker)
        t2 = threading.Thread(target=symphony_worker)
        
        t1.start()
        t2.start()
        
        # Собираем результаты
        minile_reply = ""
        script_result = ""
        
        # Собираем результаты с диагностикой
        received = 0
        for _ in range(2):
            try:
                result_type, result_data = results.get(timeout=10)  # Короче timeout
                received += 1
                if result_type == 'minile':
                    minile_reply = result_data
                    logging.info(f"✅ MiniLE completed: {len(result_data)} chars")
                elif result_type == 'symphony':
                    script_result = result_data
                    logging.info(f"✅ Symphony completed: {len(result_data)} chars")
                elif result_type == 'minile_error':
                    logging.error(f"❌ MiniLE error: {result_data}")
                    minile_reply = "MiniLE error occurred"
            except:
                logging.warning(f"⏰ Thread timeout after {received} results")
                break
        
        t1.join()
        t2.join()
        
        return f"{minile_reply}\n\n{script_result}" if script_result else minile_reply
            
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
