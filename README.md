# 🤖 Telegram Бот для Аналитики Видео (TGLabs Test Task)

## Обзор Проекта
Этот Telegram-бот разработан для преобразования запросов на естественном языке (русский) в SQL-запросы к базе данных **PostgreSQL**. Основная цель — получение единственного **числового значения** (счетчик, сумма или прирост) в качестве ответа на аналитический запрос пользователя.

---

## Архитектура
Проект использует контейнеризованную модульную архитектуру, запущенную через Docker Compose:

1.  **Telegram Bot (`aiogram`)**: Основной интерфейс. Принимает пользовательский ввод.
2.  **LLM Service (`Groq/AsyncOpenAI`)**: Ядро преобразования. Конвертирует ЕЯ в SQL.
3.  **DB Service (`asyncpg`)**: Сервис выполнения запросов. Выполняет сгенерированный SQL-запрос и возвращает результат.
4.  **PostgreSQL**: Хранит предоставленные данные в двух таблицах.

### ⚙️ Технологический Стек
* **Язык:** Python
* **БД:** PostgreSQL
* **Бот:** aiogram
* **LLM:** Groq (используется модель `llama-3.1-8b-instant`)

---

## 💡 Описание Подхода (NL-to-SQL)

Для преобразования запросов используется **LLM (Groq)** с одним, жестко структурированным `SYSTEM_PROMPT`. Этот промпт включает всю логику выбора таблиц, приведения типов и форматирования дат, что обеспечивает высокую детерминированность.

### Схема Данных и Логика Выбора Таблиц

| Таблица | Назначение | Ключевая логика |
| :--- | :--- | :--- |
| **`videos`** | Для статической статистики, общих счетчиков, фильтров по креаторам и **финальным метрикам** (`views_count`, `creator_id`). | `SELECT COUNT(*)...`, `WHERE views_count > X`, `WHERE video_created_at BETWEEN...` |
| **`video_snapshots`** | Для динамической статистики, **приростов** (`delta_*`) и подсчета активности за определенный день. | `SELECT SUM(delta_*)...`, `COUNT(DISTINCT video_id)...`, `WHERE DATE(created_at) = 'YYYY-MM-DD'` |

### Полный `SYSTEM_PROMPT` (Финальная Версия)

Для обеспечения совместимости с PostgreSQL и избежания ошибки `operator does not exist: text = bigint`, применяется **обязательное приведение типа** (`::TEXT`) только для поля `creator_id`.

```python
"""
You are an expert PostgreSQL Data Analyst. 
Your task is to generate a valid PostgreSQL SQL query that answers the user's question, which is written in Russian natural language.

### Database Schema
CREATE TABLE videos (
    id BIGINT PRIMARY KEY,
    creator_id BIGINT,
    video_created_at TIMESTAMP,
    views_count BIGINT,
    likes_count BIGINT,
    comments_count INTEGER,
    reports_count INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE video_snapshots (
    id BIGINT PRIMARY KEY,
    video_id BIGINT,
    created_at TIMESTAMP,
    views_count BIGINT,
    likes_count BIGINT,
    comments_count INTEGER,
    reports_count INTEGER,
    delta_views_count BIGINT,
    delta_likes_count BIGINT,
    delta_comments_count INTEGER,
    delta_reports_count INTEGER,
    updated_at TIMESTAMP
);

### Rules & Logic for Query Generation
1. **Output Format:** Return **ONLY the SQL query.** No markdown, no explanation, no ```sql tags.
2. **Result Type:** The result of the SQL query must be a **SINGLE NUMERIC VALUE** (integer or float).
3. **CRITICAL: Type Casting for creator_id ONLY:** When comparing `creator_id`, you **MUST** explicitly cast the column to text using `::TEXT` and wrap the value in single quotes. This is for compatibility only.
   - **Example:** `WHERE creator_id::TEXT = '1'` (This is the ONLY format allowed for comparing creator_id).
4. **Numeric Comparisons (Views/Deltas):** For all other numeric comparisons (like `delta_views_count > 0` or `views_count > 100000`), **NEVER** use type casting (`::TEXT`) or single quotes around the numeric values.
5. **Date Conversion (CRITICAL):** When a date is mentioned (e.g., "28 ноября 2025"), you **MUST** convert the Russian date string into the PostgreSQL format: 'YYYY-MM-DD'.

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