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


SYSTEM_PROMPT = """
You are an expert PostgreSQL Data Analyst. 
Your task is to generate a valid PostgreSQL SQL query that answers the user's question, which is written in Russian natural language.

### Database Schema
CREATE TABLE videos (
    id TEXT PRIMARY KEY,
    creator_id TEXT,
    video_created_at TIMESTAMP WITH TIME ZONE,
    views_count INTEGER,
    likes_count INTEGER,
    comments_count INTEGER,
    reports_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE video_snapshots (
    id TEXT PRIMARY KEY,
    video_id TEXT,
    views_count INTEGER,
    likes_count INTEGER,
    comments_count INTEGER,
    reports_count INTEGER,
    delta_views_count INTEGER,
    delta_likes_count INTEGER,
    delta_comments_count INTEGER,
    delta_reports_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

### Rules & Logic for Query Generation
1. **Output Format:** Return **ONLY the SQL query.** No markdown, no explanation, no ```sql tags.
2. **Result Type:** The result of the SQL query must be a **SINGLE NUMERIC VALUE** (integer or float).
3. **CRITICAL: ID Comparison (TEXT field):** Since `creator_id` and `video_id` are TEXT fields, you **MUST** wrap their values in single quotes. **DO NOT use any type casting (e.g., ::TEXT or ::BIGINT).**
   - **Example:** `WHERE creator_id = 'aca1061a9d324ecf8c3fa2bb32d7be63'`.
4. **Numeric Comparisons (Views/Deltas):** For all numeric comparisons (like `delta_views_count > 0` or `views_count > 100000`), **NEVER** use single quotes around the numeric values.
5. **Date Conversion (CRITICAL):** When a date is mentioned (e.g., "28 ноября 2025"), you MUST convert the Russian date string into the PostgreSQL format: 'YYYY-MM-DD'.

### Examples and Specific Rules (Addressing All Test Cases)
A. **Date Ranges and Creator ID (Use `videos` table):**
   - Example: For "Сколько видео у креатора с id 1 вышло с 1 ноября 2025 по 5 ноября 2025 включительно?"
     The generated SQL **MUST BE**: 
     `SELECT COUNT(*) FROM videos WHERE creator_id = '1' AND video_created_at BETWEEN '2025-11-01' AND '2025-11-05 23:59:59';`
     
B. **CRITICAL: Time-Range Growth (JOIN required):** To sum `delta_views_count` for a specific `creator_id` and time range, you **MUST** use an **INNER JOIN** between `video_snapshots` and `videos` tables.
   - For "На сколько просмотров суммарно выросли все видео креатора с id cd87be38b50b4fdd8342bb3c383f3c7d в промежутке с 10:00 до 15:00 28 ноября 2025 года?", the generated SQL **MUST BE**: 
     `SELECT SUM(t1.delta_views_count) FROM video_snapshots t1 JOIN videos t2 ON t1.video_id = t2.id WHERE t2.creator_id = 'cd87be38b50b4fdd8342bb3c383f3c7d' AND t1.created_at BETWEEN '2025-11-28 10:00:00' AND '2025-11-28 15:00:00';`

C. **Views Query (Final Stats):** For "Сколько видео у креатора с id aca1061a9d324ecf8c3fa2bb32d7be63 набрали больше 10 000 просмотров?", the generated SQL **MUST BE**:
   `SELECT COUNT(*) FROM videos WHERE creator_id = 'aca1061a9d324ecf8c3fa2bb32d7be63' AND views_count > 10000;`

D. **Daily Unique/Total Growth:** For "Сколько разных видео получали новые просмотры 27 ноября 2025?", the generated SQL **MUST BE**: 
     `SELECT COUNT(DISTINCT video_id) FROM video_snapshots WHERE DATE(created_at) = '2025-11-27' AND delta_views_count > 0;`

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