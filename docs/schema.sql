-- TOBI-XAUUSD Core Database Schema Blueprint

-- 1. Create the Users table to store registered members
CREATE TABLE IF NOT EXISTS users (
    -- Telegram User IDs are very long numbers, so we use BIGINT
    telegram_id BIGINT PRIMARY KEY,
    
    -- Store their Telegram handle and names securely
    username VARCHAR(100),
    first_name VARCHAR(100) NOT NULL,
    
    -- Security role: 'guest', 'user', 'admin' (Defaults to guest)
    role VARCHAR(20) DEFAULT 'guest' NOT NULL,
    
    -- Licence tier: 'free', 'premium', 'lifetime' (Defaults to free)
    license_tier VARCHAR(20) DEFAULT 'free' NOT NULL,
    
    -- Automatically records the exact millisecond they registered
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Tracks the last time they clicked a button or interacted
    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 2. Add an optimization index
-- Indexes make searching through thousands of user rows incredibly fast
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);