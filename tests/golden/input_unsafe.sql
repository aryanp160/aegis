-- Unsafe PostgreSQL migration for golden test suite

-- AEG-101: Missing CONCURRENTLY on CREATE INDEX
CREATE INDEX idx_users_email ON users (email);

-- AEG-102: Missing CONCURRENTLY on DROP INDEX
DROP INDEX idx_users_email;

-- AEG-103: Unsafe NOT NULL column addition
ALTER TABLE users ADD COLUMN age INT NOT NULL;

-- AEG-103 (Edge Case): Setting existing column to NOT NULL
ALTER TABLE users ALTER COLUMN age SET NOT NULL;

-- AEG-104: Table rewriting type conversion
ALTER TABLE users ALTER COLUMN age TYPE TEXT;

-- AEG-105: Foreign key without NOT VALID
ALTER TABLE orders ADD CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users (id);

-- AEG-105 (Edge Case): Inline foreign key reference during ADD COLUMN
ALTER TABLE orders ADD COLUMN user_id INT REFERENCES users (id);

-- AEG-106: CONCURRENTLY inside transaction
BEGIN;
CREATE INDEX CONCURRENTLY idx_users_status ON users (status);
COMMIT;

-- AEG-107: Destructive DROP TABLE (without override comment)
DROP TABLE archive_users;

-- AEG-108: SERIAL usage
CREATE TABLE profiles (id SERIAL PRIMARY KEY);

-- AEG-109: Missing SET lock_timeout is implicitly active here since no statement sets it.
-- AEG-110: TIMESTAMP WITHOUT TIME ZONE
CREATE TABLE events (created_at TIMESTAMP);
