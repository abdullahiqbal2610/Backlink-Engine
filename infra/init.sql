-- 1. platforms: platform configs, limits, proxy settings
CREATE TABLE IF NOT EXISTS platforms (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    scrape_type VARCHAR(50) NOT NULL, -- e.g., 'API', 'HTML', 'JS_DYNAMIC'
    posting_type VARCHAR(50) NOT NULL, -- e.g., 'A', 'B', 'C'
    daily_rate_limit INT DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. accounts: bot accounts or auth tokens per platform
CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    platform_name VARCHAR(255) REFERENCES platforms(name),
    username VARCHAR(255),
    auth_token TEXT,
    is_warmup_mode BOOLEAN DEFAULT TRUE,
    karma_score INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. threads: the actual content we discovered (Dedup + Tracker)
CREATE TABLE IF NOT EXISTS threads (
    thread_id UUID PRIMARY KEY,
    platform VARCHAR(255) REFERENCES platforms(name),
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    status VARCHAR(50) DEFAULT 'discovered', -- discovered, processing, relevant, irrelevant, drafted, approved, rejected
    is_relevant BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. post_results: tracking what happened after we posted
CREATE TABLE IF NOT EXISTS post_results (
    id SERIAL PRIMARY KEY,
    thread_id UUID REFERENCES threads(thread_id),
    post_status VARCHAR(50), -- success, failed, retry
    post_url TEXT,
    error_log TEXT,
    retry_count INT DEFAULT 0,
    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    backlink_live BOOLEAN DEFAULT FALSE,
    backlink_verified_at TIMESTAMP
);

-- 5. platform_guidelines: cached subreddit/forum rules
CREATE TABLE IF NOT EXISTS platform_guidelines (
    platform VARCHAR(255) PRIMARY KEY,
    url VARCHAR(512),
    rules_text TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. cookie_vault: store playwright session cookies
CREATE TABLE IF NOT EXISTS cookie_vault (
    platform VARCHAR(255),
    account_username VARCHAR(255),
    cookies_json TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (platform, account_username)
);

-- 7. discovered_platforms: new sites discovered by LLM parser
CREATE TABLE IF NOT EXISTS discovered_platforms (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(255) UNIQUE NOT NULL,
    sample_url TEXT,
    ai_summary TEXT,
    guidelines TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
