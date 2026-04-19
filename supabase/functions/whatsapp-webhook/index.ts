import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

// ── Environment Variables ─────────────────────────────────────────────────────
const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
const WHATSAPP_ACCESS_TOKEN = Deno.env.get("WHATSAPP_ACCESS_TOKEN")!
const WHATSAPP_PHONE_NUMBER_ID = Deno.env.get("WHATSAPP_PHONE_NUMBER_ID")!
const GEMINI_API_KEY = Deno.env.get("GEMINI_API_KEY")!
const WEBHOOK_VERIFY_TOKEN = Deno.env.get("WEBHOOK_VERIFY_TOKEN")! 
const WHATSAPP_APP_SECRET = Deno.env.get("WHATSAPP_APP_SECRET") // Optional in V1, but logic is ready

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

// ── Helpers ──────────────────────────────────────────────────────────────────

async function verifySignature(req: Request, payload: string): Promise<boolean> {
  const signature = req.headers.get("X-Hub-Signature-256")
  if (!WHATSAPP_APP_SECRET || !signature) return true // Skip if secret not configured yet
  
  const hmac = signature.split("sha256=")[1]
  const encoder = new TextEncoder()
  const key = await crypto.subtle.importKey(
    "raw", encoder.encode(WHATSAPP_APP_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false, ["verify"]
  )
  const verified = await crypto.subtle.verify(
    "HMAC", key, 
    hexToBytes(hmac), encoder.encode(payload)
  )
  return verified
}

function hexToBytes(hex: string) {
  const bytes = new Uint8Array(hex.length / 2)
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substr(i, 2), 16)
  }
  return bytes
}

async function sendWhatsApp(to: string, body: string) {
  const res = await fetch(`https://graph.facebook.com/v17.0/${WHATSAPP_PHONE_NUMBER_ID}/messages`, {
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
  
  if (!res.ok) {
    const errorData = await res.json()
    throw new Error(`WhatsApp API Error: ${JSON.stringify(errorData)}`)
  }
}

async function extractWithGemini(text: string, model_name = "gemini-flash-latest", retries = 5) {
  let prompt = text
  if (!text.includes("{") && !text.toLowerCase().includes("window")) {
    prompt = `Return ONLY JSON: {
      "categories": ["List all that apply: Prepared Meals, Produce, Bakery, Dairy, Meat/Protein, Beverage, Pantry"], 
      "quantity_lb": number, 
      "food_description": "short summary",
      "item_list": "bulleted list of all items",
      "requires_review": boolean
    }. Input: "${text}"`
  }
  
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model_name}:generateContent?key=${GEMINI_API_KEY}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
      })
      
      if (!res.ok) {
        if (res.status === 429 || res.status === 503) {
          const delay = Math.pow(2, i) * 2000 // Patient backoff
          console.warn(`Gemini Error (${res.status}). Retrying in ${delay}ms...`)
          await new Promise(resolve => setTimeout(resolve, delay))
          continue
        }
        throw new Error(`Gemini API error: ${res.status}`)
      }

      const data = await res.json()
      const rawText = data.candidates[0].content.parts[0].text
      return JSON.parse(rawText.replace(/```json|```/g, "").trim())
    } catch (e) {
      if (i === retries - 1) {
        if (model_name === "gemini-flash-latest") {
           console.warn("Flash failed, falling back to Lite...")
           return extractWithGemini(text, "gemini-flash-lite-latest", 3)
        }
        console.error("Gemini Final Failure:", e)
        return null // Caller handles fallback to mock/previous data
      }
    }
  }
}

async function extractWindowWithGemini(text: string) {
  const today = new Date().toISOString().split('T')[0]
  const prompt = `Today is ${today}. Extract date and end time from: "${text}". Return ONLY JSON: {"date": "YYYY-MM-DD", "end_time": "HH:MM"}`
  
  try {
    const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key=${GEMINI_API_KEY}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
    })
    const data = await res.json()
    const rawText = data.candidates[0].content.parts[0].text
    return JSON.parse(rawText.replace(/```json|```/g, "").trim())
  } catch (e) {
    console.error("Window AI Error:", e)
    return { date: today, end_time: "17:00" }
  }
}

// ── Main Server ───────────────────────────────────────────────────────────────

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
    const rawBody = await req.text()
    
    // Security: Verify X-Hub-Signature-256
    if (!(await verifySignature(req, rawBody))) {
      return new Response("Invalid Signature", { status: 401 })
    }

    const body = JSON.parse(rawBody)
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
      .maybeSingle()

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
      let details = await extractWithGemini(text)
      if (!details) {
         // Final Fallback: Simple extraction
         details = { categories: ["Pantry"], quantity_lb: 5, food_description: text.slice(0,30), item_list: `- ${text}`, requires_review: true }
      }
      const newData = { ...session.temp_data, ...details }
      
      await supabase.table("whatsapp_sessions").update({
        state: "AWAITING_REVIEW",
        temp_data: newData
      }).eq("phone_number", phone)

      const cats = details.categories.join(", ")
      await sendWhatsApp(phone, `Got it! Here is what I've captured:\n\n📋 *Items:*\n${details.item_list}\n📦 *Categories:* ${cats}\n⚖️ *Est. Weight:* ${details.quantity_lb} lbs\n\nDoes this look correct? (Reply 'Yes' or tell me what to change)`)
    } 
    else if (session.state === "AWAITING_REVIEW") {
      if (msgUpper === "YES" || msgUpper === "Y" || msgUpper === "OK") {
        await supabase.table("whatsapp_sessions").update({ state: "AWAITING_WINDOW" }).eq("phone_number", phone)
        await sendWhatsApp(phone, "Great! When is the latest we can pick this up? (e.g. 'Until 5pm today')")
      } else {
        const prompt = `Current data: ${JSON.stringify(session.temp_data)}. Update it based on: "${text}". Return updated JSON.`
        const updated = await extractWithGemini(prompt)
        
        if (updated) {
          const newData = { ...session.temp_data, ...updated }
          await supabase.table("whatsapp_sessions").update({ temp_data: newData }).eq("phone_number", phone)
          const cats = newData.categories.join(", ")
          await sendWhatsApp(phone, `Updated! How about now?\n\n📋 *Items:* ${newData.item_list}\n📦 *Categories:* ${cats}\n⚖️ *Est. Weight:* ${newData.quantity_lb} lbs\n\nReply 'Yes' to confirm or tell me what else to change.`)
        } else {
          await sendWhatsApp(phone, "Sorry, I'm having trouble updating that. Does the summary look okay now? (Reply 'Yes' or try describing the change again)")
        }
      }
    }
    else if (session.state === "AWAITING_WINDOW") {
      const today = new Date().toISOString().split('T')[0]
      const prompt = `Today is ${today}. Extract date and end time from: "${text}". Return ONLY JSON: {"date": "YYYY-MM-DD", "end_time": "HH:MM"}`
      const window = await extractWithGemini(prompt) || { date: today, end_time: "17:00" }
      
      const newData = { ...session.temp_data, ...window }
      
      await supabase.table("whatsapp_sessions").update({
        state: "AWAITING_WINDOW_REVIEW",
        temp_data: newData
      }).eq("phone_number", phone)

      await sendWhatsApp(phone, `Got it! I've scheduled the pickup for:\n\n📅 *Date:* ${window.date}\n🕒 *Latest Pickup:* ${window.end_time}\n\nDoes this work? (Reply 'Yes' or tell me what to change)`)
    }
    else if (session.state === "AWAITING_WINDOW_REVIEW") {
      if (msgUpper === "YES" || msgUpper === "Y" || msgUpper === "OK") {
        const cats = session.temp_data.categories.join(", ")
        const taskData = {
          encrypted_id: `wa_${phone.slice(-4)}_${crypto.randomUUID().split('-')[0]}`,
          date: session.temp_data.date,
          start_time: "09:00",
          end_time: session.temp_data.end_time,
          donor_name: `WhatsApp Donor (${phone.slice(-4)})`,
          address_json: { street: "Unknown (WA Lead)", city: "SF", state: "CA", zip: "94105" },
          lat: 37.7749,
          lon: -122.4194,
          food_description: session.temp_data.food_description,
          category: cats,
          quantity_lb: session.temp_data.quantity_lb,
          requires_review: session.temp_data.requires_review || false,
          donor_whatsapp_id: phone,
          status: "available"
        }

        const { error: insertError } = await supabase.table("tasks").insert(taskData)
        if (insertError) throw insertError

        await supabase.table("whatsapp_sessions").update({ state: "COMPLETED" }).eq("phone_number", phone)
        await sendWhatsApp(phone, `✅ Success! Your donation is live for ${session.temp_data.date} until ${session.temp_data.end_time}. A volunteer will be notified. Thank you! 🥕`)
      } else {
        const today = new Date().toISOString().split('T')[0]
        const prompt = `Today is ${today}. Current window: ${session.temp_data.date} ${session.temp_data.end_time}. Update based on: "${text}". Return JSON: {"date": "YYYY-MM-DD", "end_time": "HH:MM"}`
        const updated = await extractWithGemini(prompt)

        if (updated) {
          const newData = { ...session.temp_data, ...updated }
          await supabase.table("whatsapp_sessions").update({ temp_data: newData }).eq("phone_number", phone)
          await sendWhatsApp(phone, `Updated! How about now?\n\n📅 *Date:* ${newData.date}\n🕒 *Latest Pickup:* ${newData.end_time}\n\nReply 'Yes' to confirm or tell me what else to change.`)
        } else {
          await sendWhatsApp(phone, "Sorry, I'm having trouble updating the time. Is the current time okay? (Reply 'Yes' or try again)")
        }
      }
    }
    else if (session.state === "COMPLETED") {
      await sendWhatsApp(phone, "Your donation is logged. Type 'NEW' to report more surplus food!")
    }

    return new Response("OK", { status: 200 })
  } catch (err) {
    console.error("Critical Error:", err)
    // We still return 200 to Meta to prevent infinite webhook retries, 
    // but we log the error for our own debugging.
    return new Response("Error Handled", { status: 200 })
  }
})
