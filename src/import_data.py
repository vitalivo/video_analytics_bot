import asyncio
import ujson
import os
import asyncpg
import logging
from src.config import DB_DSN
from dateutil import parser # Импортируем парсер

# Утилитарная функция для безопасного парсинга даты
def parse_date_safe(date_str):
    if date_str:
        try:
            return parser.isoparse(date_str)
        except Exception as e:
            logging.warning(f"Failed to parse date string: {date_str}. Error: {e}")
            return None
    return None

DATA_PATH = "data/data.json"

async def import_json():
    logging.basicConfig(level=logging.INFO) # Убедимся, что логирование включено
    logging.info("Starting data import...")
    if not os.path.exists(DATA_PATH):
        logging.error(f"File {DATA_PATH} not found!")
        return

    conn = await asyncpg.connect(DB_DSN)
    
    try:
        # ... (Блок загрузки и распаковки JSON остается прежним) ...
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            raw_data = ujson.load(f)
        
        if isinstance(raw_data, dict) and 'videos' in raw_data:
            data = raw_data['videos']
        elif isinstance(raw_data, list):
            data = raw_data
        else:
            logging.error("JSON structure is not recognized.")
            return

        logging.info(f"Loaded JSON. Found {len(data)} videos.")

        videos_rows = []
        snapshots_rows = []

        for v in data:
            videos_rows.append((
                v['id'], v['creator_id'], 
                # !!! ПАРСИНГ ДАТ: video_created_at, created_at, updated_at !!!
                parse_date_safe(v['video_created_at']), 
                v['views_count'], v['likes_count'], v['comments_count'], v['reports_count'],
                parse_date_safe(v.get('created_at')), 
                parse_date_safe(v.get('updated_at'))
            ))
            
            for s in v.get('snapshots', []):
                snapshots_rows.append((
                    s['id'], s['video_id'],
                    s['views_count'], s['likes_count'], s['comments_count'], s['reports_count'],
                    s['delta_views_count'], s['delta_likes_count'], s['delta_comments_count'], s['delta_reports_count'],
                    # !!! ПАРСИНГ ДАТ: created_at, updated_at в снапшотах !!!
                    parse_date_safe(s['created_at']), 
                    parse_date_safe(s.get('updated_at'))
                ))

        logging.info(f"Inserting {len(videos_rows)} videos...")
        await conn.copy_records_to_table(
            'videos', 
            records=videos_rows,
            columns=['id', 'creator_id', 'video_created_at', 'views_count', 'likes_count', 'comments_count', 'reports_count', 'created_at', 'updated_at']
        )
        
        # ... (Остальная часть импорта снапшотов без изменений)
        logging.info(f"Inserting {len(snapshots_rows)} snapshots...")
        await conn.copy_records_to_table(
            'video_snapshots',
            records=snapshots_rows,
            columns=['id', 'video_id', 'views_count', 'likes_count', 'comments_count', 'reports_count', 
                     'delta_views_count', 'delta_likes_count', 'delta_comments_count', 'delta_reports_count', 
                     'created_at', 'updated_at']
        )
        
        logging.info("Import completed successfully.")

    except Exception as e:
        logging.error(f"Error during import: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(import_json())