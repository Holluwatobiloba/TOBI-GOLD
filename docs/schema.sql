-- TOBI-XAUUSD Core Database Schema Blueprint

-- 1. Create the Users table to store registered members
CREATE TABLE IF NOT EXISTS users (
    telegram_id BIGINT PRIMARY KEY,
    username VARCHAR(100),
    first_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) DEFAULT 'guest' NOT NULL,
    license_tier VARCHAR(20) DEFAULT 'free' NOT NULL,
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_active_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Optimization Index for rapid user queries
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);


-- 2. Create the Signals table to log gold trading setups
CREATE TABLE IF NOT EXISTS signals (
    -- Unique, auto-incrementing ID for every signal we generate
    signal_id SERIAL PRIMARY KEY,
    
    -- The financial asset (Always 'XAUUSD' for this core system)
    pair VARCHAR(20) DEFAULT 'XAUUSD' NOT NULL,
    
    -- Direction: 'BUY', 'SELL', 'BUY_LIMIT', 'SELL_LIMIT'
    direction VARCHAR(15) NOT NULL,
    
    -- Precise entry and risk target prices
    entry_price NUMERIC(10, 2) NOT NULL,
    stop_loss NUMERIC(10, 2) NOT NULL,
    take_profit NUMERIC(10, 2) NOT NULL,
    
    -- Trade Status: 'pending', 'active', 'tp_hit', 'sl_hit', 'cancelled'
    status VARCHAR(20) DEFAULT 'pending' NOT NULL,
    
    -- Optional context or notes about the setup (e.g., "London session liquidity sweep")
    notes TEXT,
    
    -- Tracks the admin who issued the signal
    created_by BIGINT REFERENCES users(telegram_id) ON DELETE SET NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Optimization Index for filtering active vs closed trade setups
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);