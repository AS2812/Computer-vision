const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, authorization, apikey",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function json(statusCode, body) {
  return {
    statusCode,
    headers: { ...CORS, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export async function handler(event) {
  if (event.httpMethod === "OPTIONS") return { statusCode: 204, headers: CORS, body: "" };
  if (event.httpMethod !== "POST") return json(405, { error: "Method not allowed" });

  const supabaseUrl = process.env.VITE_SUPABASE_URL || process.env.SUPABASE_URL;
  const anonKey = process.env.VITE_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY;
  if (!supabaseUrl || !anonKey) return json(503, { error: "Supabase analyze proxy is not configured" });

  try {
    const res = await fetch(`${supabaseUrl.replace(/\/$/, "")}/functions/v1/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        apikey: anonKey,
        Authorization: `Bearer ${anonKey}`,
      },
      body: event.body || "{}",
      signal: AbortSignal.timeout(75_000),
    });
    const text = await res.text();
    return {
      statusCode: res.status,
      headers: { ...CORS, "Content-Type": res.headers.get("Content-Type") || "application/json" },
      body: text,
    };
  } catch {
    return json(502, { error: "Supabase analyze request failed" });
  }
}
