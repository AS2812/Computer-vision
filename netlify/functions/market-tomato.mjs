const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
};

const OBOOR_URL = "http://www.oboormarket.org.eg/prices_today.aspx";

function json(statusCode, body) {
  return {
    statusCode,
    headers: { ...CORS, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

function unavailable(reason) {
  return {
    crop: "tomato",
    market: "El-Obour wholesale market",
    low_egp_per_kg: null,
    high_egp_per_kg: null,
    unit: "EGP/kg",
    source: "El-Obour Market official daily prices",
    source_url: OBOOR_URL,
    as_of: new Date().toISOString().slice(0, 10),
    live: false,
    note: `${reason} No live tomato price is shown; enter a local market quote instead.`,
  };
}

function parseTomatoPrice(html) {
  const text = html.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
  const patterns = [
    /طماطم.{0,300}?من\s*سعر\s*:?\s*([0-9]+(?:\.[0-9]+)?)\s*الى\s*سعر\s*:?\s*([0-9]+(?:\.[0-9]+)?)/i,
    /طماطم.{0,300}?([0-9]+(?:\.[0-9]+)?)\s*(?:-|–|الى|إلى)\s*([0-9]+(?:\.[0-9]+)?)/i,
  ];
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (!match) continue;
    const a = Number(match[1]);
    const b = Number(match[2]);
    if (Number.isFinite(a) && Number.isFinite(b)) return [Math.min(a, b), Math.max(a, b)];
  }
  return null;
}

export async function handler(event) {
  if (event.httpMethod === "OPTIONS") return { statusCode: 204, headers: CORS, body: "" };
  if (event.httpMethod !== "GET") return json(405, { error: "Method not allowed" });

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 7000);
    const res = await fetch(OBOOR_URL, { signal: controller.signal });
    clearTimeout(timeout);
    if (!res.ok) return json(200, unavailable(`Official market page returned ${res.status}.`));
    const html = await res.text();
    const parsed = parseTomatoPrice(html);
    if (!parsed) return json(200, unavailable("Could not parse the tomato row from the live market page."));
    const [low, high] = parsed;
    return json(200, {
      crop: "tomato",
      market: "El-Obour wholesale market",
      low_egp_per_kg: low,
      high_egp_per_kg: high,
      unit: "EGP/kg",
      source: "El-Obour Market official daily prices",
      source_url: OBOOR_URL,
      as_of: new Date().toISOString().slice(0, 10),
      live: true,
      note: "Wholesale tomato range from the official El-Obour daily price page; retail and farmgate prices differ.",
    });
  } catch {
    return json(200, unavailable("Live market page unavailable."));
  }
}
