import asyncpg
import logging
from src.config import DB_DSN

logger = logging.getLogger(__name__)

# Глобальная переменная для пула
pool = None

async def get_db_pool():
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(DB_DSN)
    return pool

async def execute_sql_query(query: str) -> float | int | None:
    global pool
    if pool is None:
        # Пул должен быть инициализирован при запуске бота, но на всякий случай
        await get_db_pool() 

    logger.info(f"Executing SQL: {query}")

    try:
        # 1. Получаем соединение из пула
        # 2. Используем fetchval для получения ОДНОГО значения (как в случае с COUNT)
        result = await pool.fetchval(query)
        
        # asyncpg возвращает числа в нативном Python-формате (int/float), 
        # но мы убедимся, что возвращаемое значение - число (или None).
        if result is None:
            return None
        
        # Если это строка (что маловероятно для COUNT), пытаемся преобразовать в число
        if isinstance(result, (int, float)):
            return result
        
        # Если LLM вернул не COUNT, а что-то другое (например, строку)
        try:
            return float(result) if '.' in str(result) else int(result)
        except ValueError:
            logger.warning(f"SQL returned non-numeric value: {result}")
            return None

    except Exception as e:
        logger.error(f"SQL Execution Error on query: {query}. Error: {e}", exc_info=True)
        return None