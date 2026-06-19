// Resilient Supabase client. The app is fully usable WITHOUT Supabase — when the
// env vars are absent, `supabase` is null and the UI falls back to local-only
// screening (in-browser ONNX), no AI second opinion, no cloud logging.

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const supabase: SupabaseClient | null = url && anonKey ? createClient(url, anonKey) : null;

/** The analyze Edge Function URL (override via VITE_ANALYZE_FUNCTION_URL). */
const analyzeOverride = import.meta.env.VITE_ANALYZE_FUNCTION_URL as string | undefined;
export const analyzeFunctionUrl: string | null =
  analyzeOverride === "disabled" || analyzeOverride === "off"
    ? null
    : analyzeOverride ?? (import.meta.env.DEV ? (url ? `${url.replace(/\/$/, "")}/functions/v1/analyze` : null) : "/.netlify/functions/analyze");

/** The hosted crop assistant Edge Function URL — routes through Netlify proxy in production. */
export const assistantFunctionUrl: string | null =
  (import.meta.env.VITE_ASSISTANT_FUNCTION_URL as string | undefined) ??
  (import.meta.env.DEV
    ? (url ? `${url.replace(/\/$/, "")}/functions/v1/assistant` : null)
    : "/.netlify/functions/assistant");

export const supabaseConfigured = Boolean(supabase);

let signInStarted = false;

/** Sign in anonymously once (best-effort). Safe to call repeatedly. */
export async function ensureAnonAuth(): Promise<void> {
  if (!supabase || signInStarted) return;
  signInStarted = true;
  try {
    const { data } = await supabase.auth.getSession();
    if (!data.session) await supabase.auth.signInAnonymously();
  } catch {
    // Anonymous auth may be disabled on the project; non-fatal.
  }
}
