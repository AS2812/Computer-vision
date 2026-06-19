# AgroVision Free-Tier Hosting

Target setup:

- Netlify Free: React/Vite frontend.
- Supabase Free: Postgres, anonymous auth, `analyze` Edge Function, `assistant` Edge Function.
- Optional Render Free: legacy FastAPI compatibility backend for `/api/market`, `/api/treatments`, and old report endpoints while those are migrated.

## 1. Supabase

Create a dedicated Supabase project named `AgroVision Egypt` on the Free plan.
Do not reuse unrelated projects such as school, marketplace, or production apps.

Apply the local migrations in order from `supabase/migrations/`.

Deploy Edge Functions:

```powershell
supabase functions deploy analyze --project-ref YOUR_PROJECT_REF
supabase functions deploy assistant --project-ref YOUR_PROJECT_REF
```

Set function secrets:

```powershell
supabase secrets set EXTERNAL_LLM_API_URL=https://opencode.ai/zen/v1/chat/completions --project-ref YOUR_PROJECT_REF
supabase secrets set EXTERNAL_LLM_API_KEY=YOUR_OPEN_CODE_ZEN_KEY --project-ref YOUR_PROJECT_REF
supabase secrets set EXTERNAL_LLM_MODEL=deepseek-v4-flash-free --project-ref YOUR_PROJECT_REF
supabase secrets set EXTERNAL_VISION_MODEL=mimo-v2.5-free --project-ref YOUR_PROJECT_REF
supabase secrets set EXTERNAL_LLM_MAX_TOKENS=2000 --project-ref YOUR_PROJECT_REF
supabase secrets set EXTERNAL_LLM_REASONING_EFFORT=low --project-ref YOUR_PROJECT_REF
```

In Supabase Auth, enable anonymous sign-ins if you want per-session anonymous logging.
The app still calls Edge Functions with the anon key when anonymous sign-in is disabled.

## 2. Netlify

Create a Netlify site from this repo.

Build settings are already in `netlify.toml`:

- Build command: `pnpm --filter @agrovision/web build`
- Publish directory: `apps/web/dist`

Set Netlify environment variables:

```text
VITE_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
VITE_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
```

Optional, only if you deploy Render:

```text
VITE_API_URL=https://YOUR_RENDER_SERVICE.onrender.com
```

Do not put `EXTERNAL_LLM_API_KEY` in Netlify. It belongs only in Supabase Edge Function secrets or Render server env.

## 3. Optional Render Free Backend

Use `render.yaml` if you want the old FastAPI endpoints online too.

Render Free sleeps after inactivity, so first requests may take about a minute.

Set Render secrets:

```text
EXTERNAL_LLM_API_KEY=YOUR_OPEN_CODE_ZEN_KEY
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY
```

Then set Netlify `VITE_API_URL` to the Render service URL.

## 4. Free-Tier Reality

This is suitable for demos, MVP testing, and low-traffic farmer pilots.
Free tiers can sleep, pause, or hit bandwidth/build quotas. For real public production,
upgrade Supabase first, then the backend if usage grows.
