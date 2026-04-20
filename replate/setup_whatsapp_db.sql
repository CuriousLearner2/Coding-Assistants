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
ADD COLUMN IF NOT EXISTS requires_review BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now(),
ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS released_at TIMESTAMPTZ;

-- 3. Enable RLS (Security)
ALTER TABLE whatsapp_sessions ENABLE ROW LEVEL SECURITY;

-- 4. Allow access to sessions (Only for the Edge Function via Service Role)
CREATE POLICY "Service Role Only" ON whatsapp_sessions FOR ALL TO service_role USING (auth.role() = 'service_role');

-- 5. Index for TTL performance
CREATE INDEX IF NOT EXISTS idx_whatsapp_sessions_updated_at ON whatsapp_sessions(updated_at);

-- 6. Trigger for Status Notifications
-- This requires the 'net' extension to be enabled in Supabase
CREATE EXTENSION IF NOT EXISTS "net";

CREATE OR REPLACE FUNCTION public.on_task_status_change_notify()
RETURNS TRIGGER AS $$
BEGIN
  -- We use the net.http_post to call the Edge Function.
  -- Replace <YOUR_PROJECT_REF> and <YOUR_ANON_KEY> with actual values 
  -- or use the Supabase Dashboard UI to set up a Database Webhook instead.
  PERFORM
    net.http_post(
      url := 'https://' || (SELECT setting FROM pg_settings WHERE name = 'request_host') || '/functions/v1/whatsapp-status-notifications',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'Authorization', 'Bearer ' || (SELECT setting FROM pg_settings WHERE name = 'anon_key')
      ),
      body := jsonb_build_object(
        'type', TG_OP,
        'record', row_to_json(NEW),
        'old_record', CASE WHEN TG_OP = 'UPDATE' THEN row_to_json(OLD) ELSE NULL END
      )
    );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Uncomment the line below ONLY if you want to use raw SQL triggers 
-- instead of the Supabase Dashboard Webhooks UI.
-- CREATE TRIGGER trigger_task_notifications AFTER INSERT OR UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION on_task_status_change_notify();
