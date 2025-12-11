-- init.sql
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY, -- ИЗМЕНЕНО с BIGINT на TEXT
    creator_id TEXT,     -- ИЗМЕНЕНО с BIGINT на TEXT
    video_created_at TIMESTAMP WITH TIME ZONE,
    views_count INTEGER,
    likes_count INTEGER,
    comments_count INTEGER,
    reports_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS video_snapshots (
    id TEXT PRIMARY KEY,   -- ИЗМЕНЕНО с BIGINT на TEXT
    video_id TEXT REFERENCES videos(id), -- ИЗМЕНЕНО с BIGINT на TEXT
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

-- Индексы для ускорения поиска по датам
CREATE INDEX idx_videos_created_at ON videos(video_created_at);
CREATE INDEX idx_snapshots_created_at ON video_snapshots(created_at);
CREATE INDEX idx_videos_creator_id ON videos(creator_id);