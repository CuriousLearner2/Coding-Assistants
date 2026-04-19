-- SQL Setup for WhatsApp V1 Integration

-- 1. Create the WhatsApp Session State table
CREATE TABLE IF NOT EXISTS whatsapp_sessions (
    phone_number TEXT PRIMARY KEY,
    state TEXT DEFAULT 'START',
    temp_data JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Add technical metadata to the Tasks table
ALTER TABLE tasks 
ADD COLUMN IF NOT EXISTS requires_review BOOLEAN DEFAULT false;

-- 3. Enable RLS (Security)
ALTER TABLE whatsapp_sessions ENABLE ROW LEVEL SECURITY;

-- 4. Allow access to sessions (Only for the Edge Function via Service Role)
CREATE POLICY "Service Role Only" ON whatsapp_sessions FOR ALL TO service_role USING (auth.role() = 'service_role');

-- 5. Index for TTL performance
CREATE INDEX IF NOT EXISTS idx_whatsapp_sessions_updated_at ON whatsapp_sessions(updated_at);
