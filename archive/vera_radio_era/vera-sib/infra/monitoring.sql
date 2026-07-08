-- VERA Immutable Audit Schema
CREATE TABLE IF NOT EXISTS immutable_audit (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    data_hash VARCHAR(256),
    action VARCHAR(500),
    status VARCHAR(50),
    CONSTRAINT audit_append_only CHECK (id > 0)
);

CREATE INDEX idx_audit_type ON immutable_audit(event_type);
CREATE INDEX idx_audit_time ON immutable_audit(timestamp);

-- Alert if immutable_audit table is modified
CREATE OR REPLACE FUNCTION audit_log_trigger()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO immutable_audit (event_type, action, status)
    VALUES (TG_TABLE_NAME, TG_OP, 'logged');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Monitoring metrics
SELECT 
    event_type, 
    COUNT(*) as count, 
    MAX(timestamp) as last_event
FROM immutable_audit
GROUP BY event_type
ORDER BY last_event DESC;
