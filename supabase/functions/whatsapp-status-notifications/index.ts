import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const handler = async (req: Request): Promise<Response> => {
  const TOK = Deno.env.get("WHATSAPP_ACCESS_TOKEN") || ""
  const ID = Deno.env.get("WHATSAPP_PHONE_NUMBER_ID") || ""
  const ADM = Deno.env.get("ADMIN_PHONE") || ""
  
  try {
    const data = await req.json()
    const rec = data.record
    const old = data.old_record
    const type = data.type
    const api = "https://graph.facebook.com/v17.0/" + ID + "/messages"

    // We only care about status changes (Updates)
    if (type === "UPDATE" && rec.status !== old.status) {
      const phone = rec.donor_whatsapp_id
      
      // 1. CLAIMED
      if (rec.status === "claimed") {
        if (phone) {
          const msg = "🙌 Good news! A volunteer has claimed your donation. They will arrive by " + rec.end_time + "."
          await fetch(api, {
            method: "POST",
            headers: { "Authorization": "Bearer " + TOK, "Content-Type": "application/json" },
            body: JSON.stringify({ messaging_product: "whatsapp", to: phone, type: "text", text: { body: msg } })
          })
        }
        await fetch(api, {
          method: "POST",
          headers: { "Authorization": "Bearer " + TOK, "Content-Type": "application/json" },
          body: JSON.stringify({ messaging_product: "whatsapp", to: ADM, type: "text", text: { body: "📢 Task " + rec.id + " CLAIMED" } })
        })
      }
      
      // 2. UNCLAIMED (Back to available)
      if (rec.status === "available" && old.status === "claimed") {
        await fetch(api, {
          method: "POST",
          headers: { "Authorization": "Bearer " + TOK, "Content-Type": "application/json" },
          body: JSON.stringify({ messaging_product: "whatsapp", to: ADM, type: "text", text: { body: "⚠️ Task " + rec.id + " UNCLAIMED" } })
        })
      }
      
      // 3. RESCUED (Completed)
      if (rec.status === "completed") {
        if (phone) {
          const msg = "✅ Pickup Complete! Thank you for your donation. 🥕"
          await fetch(api, {
            method: "POST",
            headers: { "Authorization": "Bearer " + TOK, "Content-Type": "application/json" },
            body: JSON.stringify({ messaging_product: "whatsapp", to: phone, type: "text", text: { body: msg } })
          })
        }
        await fetch(api, {
          method: "POST",
          headers: { "Authorization": "Bearer " + TOK, "Content-Type": "application/json" },
          body: JSON.stringify({ messaging_product: "whatsapp", to: ADM, type: "text", text: { body: "✅ Task " + rec.id + " RESCUED" } })
        })
      }
    }
  } catch (e) {
    console.error(e)
  }

  return new Response("OK")
}

serve(handler)
