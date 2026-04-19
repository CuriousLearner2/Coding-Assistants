import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
const WHATSAPP_ACCESS_TOKEN = Deno.env.get("WHATSAPP_ACCESS_TOKEN")!
const WHATSAPP_PHONE_NUMBER_ID = Deno.env.get("WHATSAPP_PHONE_NUMBER_ID")!
const GEMINI_API_KEY = Deno.env.get("GEMINI_API_KEY")!
const WEBHOOK_VERIFY_TOKEN = "replate_v1_secret_token" // You'll paste this into Meta Dashboard

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

serve(async (req) => {
  const { method } = req
  const url = new URL(req.url)

  // 1. WEBHOOK VERIFICATION (GET)
  if (method === "GET") {
    const mode = url.searchParams.get("hub.mode")
    const token = url.searchParams.get("hub.verify_token")
    const challenge = url.searchParams.get("hub.challenge")

    if (mode === "subscribe" && token === WEBHOOK_VERIFY_TOKEN) {
      return new Response(challenge, { status: 200 })
    }
    return new Response("Forbidden", { status: 403 })
  }

  // 2. MESSAGE PROCESSING (POST)
  try {
    const body = await req.json()
    const entry = body.entry?.[0]
    const changes = entry?.changes?.[0]
    const value = changes?.value
    const message = value?.messages?.[0]

    if (!message || message.type !== "text") {
      return new Response("OK", { status: 200 })
    }

    const phone = message.from
    const text = message.text.body.trim()
    const msgUpper = text.toUpperCase()

    // ── Handle Commands ──────────────────────────────────────────────────────

    if (msgUpper === "STOP" || msgUpper === "CANCEL") {
      await supabase.table("whatsapp_sessions").delete().eq("phone_number", phone)
      await sendWhatsApp(phone, "🛑 Session deleted. Send 'NEW' to start again.")
      return new Response("OK", { status: 200 })
    }

    // ── Get/Create Session ───────────────────────────────────────────────────

    let { data: session } = await supabase
      .table("whatsapp_sessions")
      .select("*")
      .eq("phone_number", phone)
      .single()

    if (!session || msgUpper === "RESET" || msgUpper === "NEW" || msgUpper === "START") {
      await supabase.table("whatsapp_sessions").upsert({
        phone_number: phone,
        state: "AWAITING_DESC",
        temp_data: {},
        updated_at: new Date().toISOString()
      })
      await sendWhatsApp(phone, "👋 Hi from Replate! What kind of food do you have today? (e.g. '3 trays of pasta')")
      return new Response("OK", { status: 200 })
    }

    // ── State Machine ────────────────────────────────────────────────────────

    if (session.state === "AWAITING_DESC") {
      const details = await extractWithGemini(text)
      const newData = { ...session.temp_data, ...details }
      
      await supabase.table("whatsapp_sessions").update({
        state: "AWAITING_WINDOW",
        temp_data: newData
      }).eq("phone_number", phone)

      await sendWhatsApp(phone, `Got it! ${details.food_description} (${details.category}). \n\nWhen is the latest we can pick this up?`)
    } 
    else if (session.state === "AWAITING_WINDOW") {
      const taskData = {
        encrypted_id: `wa_${phone.slice(-4)}_${Math.random().toString(36).substring(7)}`,
        date: new Date().toISOString().split('T')[0],
        start_time: "12:00",
        end_time: "17:00",
        donor_name: `WhatsApp Donor (${phone.slice(-4)})`,
        address_json: { street: "Unknown (WA Lead)", city: "SF", state: "CA", zip: "94105" },
        lat: 37.7749,
        lon: -122.4194,
        food_description: session.temp_data.food_description,
        category: session.temp_data.category,
        quantity_lb: session.temp_data.quantity_lb,
        donor_whatsapp_id: phone,
        status: "available"
      }

      await supabase.table("tasks").insert(taskData)
      await supabase.table("whatsapp_sessions").update({ state: "COMPLETED" }).eq("phone_number", phone)
      await sendWhatsApp(phone, "✅ Success! Your donation is live. A volunteer will be notified. Thank you! 🥕")
    }
    else if (session.state === "COMPLETED") {
      await sendWhatsApp(phone, "Type 'NEW' to report more surplus food!")
    }

    return new Response("OK", { status: 200 })
  } catch (err) {
    console.error(err)
    return new Response("Internal Error", { status: 500 })
  }
})

// ── Helpers ──────────────────────────────────────────────────────────────────

async function sendWhatsApp(to: string, body: string) {
  await fetch(`https://graph.facebook.com/v17.0/${WHATSAPP_PHONE_NUMBER_ID}/messages`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${WHATSAPP_ACCESS_TOKEN}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      messaging_product: "whatsapp",
      to: to,
      type: "text",
      text: { body: body }
    })
  })
}

async function extractWithGemini(text: string) {
  const prompt = `Return ONLY JSON: {"category": "One of [Prepared Meals, Produce, Bakery, Dairy, Meat/Protein, Pantry]", "quantity_lb": number, "food_description": "short string"}. Input: "${text}"`
  
  try {
    const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
    })
    const data = await res.json()
    const rawText = data.candidates[0].content.parts[0].text
    return JSON.parse(rawText.replace(/```json|```/g, "").trim())
  } catch (e) {
    return { category: "Pantry", quantity_lb: 5, food_description: text.slice(0, 50) }
  }
}
