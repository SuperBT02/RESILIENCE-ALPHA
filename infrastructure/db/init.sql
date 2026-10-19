-- ==========================================
-- PROJECT RESILIENCE-ALPHA: Database Schema
-- ==========================================

-- Enable UUID extension for secure unique identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Users Table (Stores mock clients/merchants)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Transactions Table (Core payment records)
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sender_id UUID REFERENCES users(id) ON DELETE CASCADE,
    receiver_id UUID REFERENCES users(id) ON DELETE CASCADE,
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) DEFAULT 'EUR',
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING', 'SUCCESS', 'FAILED')),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Audit Logs Table (For security monitoring / SIEM pillar)
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL, -- e.g., 'LOGIN_FAILED', 'UNAUTHORIZED_ACCESS', 'DB_STRESS'
    source_ip VARCHAR(45),
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance and query optimization under load
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);

-- Insert initial mock users for testing
INSERT INTO users (username, email, password_hash) VALUES
('alice_merchant', 'alice@resilience.local', '$2b$10$eXampleHashForDemoPurposesOnly123456789'),
('bob_customer', 'bob@resilience.local', '$2b$10$eXampleHashForDemoPurposesOnly123456789')
ON CONFLICT (username) DO NOTHING;