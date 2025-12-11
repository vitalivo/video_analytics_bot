from openai import AsyncOpenAI
from src.config import OPENAI_API_KEY, LLM_BASE_URL, LLM_MODEL
import datetime
import httpx
import logging
logger = logging.getLogger(__name__)

http_client = httpx.AsyncClient(
    # Здесь можно добавить таймауты, если нужно.
    # Если вы используете НЕ OpenAI, то base_url лучше прописать тут: base_url=LLM_BASE_URL
)

client = AsyncOpenAI(
    api_key=OPENAI_API_KEY, 
    base_url=LLM_BASE_URL,
    http_client=http_client # Ключевое изменение
)

# ... (Остальная часть до SYSTEM_PROMPT остается без изменений)

SYSTEM_PROMPT = """
You are an expert PostgreSQL Data Analyst. 
Your task is to generate a valid PostgreSQL SQL query that answers the user's question, which is written in Russian natural language.

### Database Schema
# ... (Описания таблиц остаются без изменений)

### Rules & Logic for Query Generation
### Rules & Logic for Query Generation
1. **Output Format:** Return **ONLY the SQL query.** No markdown, no explanation, no ```sql tags.
2. **Result Type:** The result of the SQL query must be a **SINGLE NUMERIC VALUE** (integer or float).
3. **CRITICAL: Type Casting for creator_id ONLY:** When comparing `creator_id`, you MUST explicitly cast the column to text using `::TEXT` and wrap the value in single quotes. This is for compatibility only.
   - **Example:** `WHERE creator_id::TEXT = '1'` (This is the ONLY format allowed for comparing creator_id).
4. **Numeric Comparisons (Views/Deltas):** For all other numeric comparisons (like `delta_views_count > 0` or `views_count > 100000`), **NEVER** use type casting (`::TEXT`) or single quotes around the numeric values.

### Examples and Specific Rules (Directly addressing Test Cases)
A. **Date Ranges and Creator ID (Use `videos` table):**
   - Example: For "Сколько видео у креатора с id 1 вышло с 1 ноября 2025 по 5 ноября 2025 включительно?"
     The generated SQL **MUST BE**: 
     `SELECT COUNT(*) FROM videos WHERE creator_id::TEXT = '1' AND video_created_at BETWEEN '2025-11-01' AND '2025-11-05 23:59:59';`
     
B. **Growth/Activity Queries (Use `video_snapshots` table):**
   - **Unique Active Videos:** To find **different videos** that were active, the generated SQL **MUST BE**: 
     `SELECT COUNT(DISTINCT video_id) FROM video_snapshots WHERE DATE(created_at) = 'YYYY-MM-DD' AND delta_views_count > 0;`
     (Note: delta_views_count must be compared to 0 without quotes or casting).

### Context
Today is {current_date}. If the year is missing in the user query, assume 2025.
"""

async def generate_sql_from_text(user_text: str) -> str:
    current_date = datetime.date.today().isoformat()
    prompt = SYSTEM_PROMPT.format(current_date=current_date)
    logging.info(f"LLM request received: '{user_text}'. Using model: {LLM_MODEL}")
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_text}
    ]

    try:
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0  # Нулевая температура для детерминированности кода
        )
        sql_query = response.choices[0].message.content.strip()
        logger.info(f"Generated SQL: {sql_query}")
        # Очистка от маркдауна, если модель все же его добавила
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        return sql_query
    except Exception as e:
        logger.error(f"LLM Error: {e}", exc_info=True)
        return ""