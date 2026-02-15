-- Initialize database schema for AI Knowledge Assistant

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tenants table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    api_key_hash VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_tenants_api_key ON tenants(api_key_hash);

-- Documents table
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text/markdown',
    metadata JSONB DEFAULT '{}',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documents_tenant ON documents(tenant_id);
CREATE INDEX idx_documents_tenant_name ON documents(tenant_id, name);

-- Queries table (AI request/result log)
CREATE TABLE queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT,
    sources JSONB DEFAULT '[]',
    confidence DECIMAL(3,2),
    insufficient_context BOOLEAN DEFAULT FALSE,
    retrieved_chunks_count INTEGER,
    llm_tokens_used INTEGER,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_queries_tenant ON queries(tenant_id);
CREATE INDEX idx_queries_tenant_created ON queries(tenant_id, created_at DESC);

-- Audit logs table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_tenant_created ON audit_logs(tenant_id, created_at DESC);

-- Insert sample tenants for testing
INSERT INTO tenants (id, name, api_key_hash, is_active) VALUES
    ('11111111-1111-1111-1111-111111111111', 'Acme Corporation', 'acme_test_key_hash', true),
    ('22222222-2222-2222-2222-222222222222', 'TechStart Inc', 'techstart_test_key_hash', true);