-- ============================================================================
-- KNOWLEDGE BASE TABLE SETUP
-- Run this in the Supabase SQL Editor to add the knowledge base feature
-- ============================================================================

-- KNOWLEDGE BASE TABLE
-- Stores parsed preference documents that give Claude "memory"
CREATE TABLE IF NOT EXISTS knowledge_base (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    document_name VARCHAR(500) NOT NULL,
    document_type VARCHAR(100) DEFAULT 'master_preferences',
    raw_text TEXT,
    parsed_content JSONB,
    raw_summary TEXT,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_base_active ON knowledge_base(is_active);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_type ON knowledge_base(document_type);

-- Auto-update timestamp trigger
DROP TRIGGER IF EXISTS update_knowledge_base_updated_at ON knowledge_base;
CREATE TRIGGER update_knowledge_base_updated_at
    BEFORE UPDATE ON knowledge_base
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SETUP COMPLETE!
-- After running this, go to the Admin Panel > Knowledge Base tab to upload
-- your preference documents.
-- ============================================================================
