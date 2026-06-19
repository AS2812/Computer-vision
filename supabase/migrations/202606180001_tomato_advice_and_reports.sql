-- ─────────────────────────────────────────────────────────────────────────────
-- Literal-spec rebuild: the `analyze` Edge Function's data layer.
--   • tomato_advice       — reviewed bilingual advice KB the gateway merges in
--                           (publicly readable; category-level, NEVER doses).
--   • anonymized_reports  — privacy-first monitoring log (no image, no GPS).
--   • storage bucket `case-images` — OPT-IN image uploads, owner-scoped via RLS.
--
-- Anonymous Auth: the web app signs in anonymously; reports are written by the
-- Edge Function with the service role (RLS-exempt), so no anon write policy is
-- needed on anonymized_reports — it stays unreadable to clients by design.
-- ─────────────────────────────────────────────────────────────────────────────

create table if not exists public.tomato_advice (
  key text primary key,
  name_en text not null,
  name_ar text not null,
  cause text not null,
  curable boolean not null default true,
  summary_en text not null default '',
  summary_ar text not null default '',
  treatment_note_en text not null default '',
  treatment_note_ar text not null default '',
  updated_at timestamptz not null default now()
);

comment on table public.tomato_advice is
  'Reviewed tomato advice merged by the analyze Edge Function. Category-level only — never contains chemical product names or doses.';

create table if not exists public.anonymized_reports (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  local_top_key text,
  ai_top_key text,
  ai_agrees boolean,
  ai_model text,
  signals jsonb not null default '{}'::jsonb,
  lang text not null default 'ar'
);

comment on table public.anonymized_reports is
  'Anonymised screening outcomes for monitoring. No image bytes, no coordinates, no user id.';

-- ── RLS ──────────────────────────────────────────────────────────────────────
alter table public.tomato_advice enable row level security;
alter table public.anonymized_reports enable row level security;

-- Advice KB is public reference data: readable by anon + authenticated, writable
-- by no one through the API (only migrations / service role manage it).
drop policy if exists "tomato_advice_read" on public.tomato_advice;
create policy "tomato_advice_read" on public.tomato_advice
  for select to anon, authenticated using (true);

-- anonymized_reports: no anon/authenticated policies at all -> only the service
-- role (Edge Function) can insert/read. Clients can never read others' reports.

-- ── Opt-in image storage ─────────────────────────────────────────────────────
insert into storage.buckets (id, name, public)
values ('case-images', 'case-images', false)
on conflict (id) do nothing;

-- Owner-scoped: a user may only touch objects under a folder named with their uid.
drop policy if exists "case_images_insert_own" on storage.objects;
create policy "case_images_insert_own" on storage.objects
  for insert to authenticated
  with check (bucket_id = 'case-images' and (storage.foldername(name))[1] = auth.uid()::text);

drop policy if exists "case_images_read_own" on storage.objects;
create policy "case_images_read_own" on storage.objects
  for select to authenticated
  using (bucket_id = 'case-images' and (storage.foldername(name))[1] = auth.uid()::text);

drop policy if exists "case_images_delete_own" on storage.objects;
create policy "case_images_delete_own" on storage.objects
  for delete to authenticated
  using (bucket_id = 'case-images' and (storage.foldername(name))[1] = auth.uid()::text);

-- ── Seed the advice KB (10 tomato classes + healthy) ─────────────────────────
-- Category-level treatment notes only. Mirrors apps/web/src/data/diseases.ts.
insert into public.tomato_advice (key, name_en, name_ar, cause, curable, treatment_note_en, treatment_note_ar) values
  ('tomato_bacterial_spot', 'Bacterial spot', 'التبقّع البكتيري', 'bacterial', true,
   'Fungicides do NOT cure bacteria. Use copper-based protection + sanitation + rotation. Confirm the registered Egyptian product and dose with an agronomist.',
   'المبيدات الفطرية ما بتشفيش البكتيريا. حماية بالنحاس + نظافة + دورة. أكّد المنتج المسجّل في مصر وجرعته مع مهندس زراعي.'),
  ('tomato_early_blight', 'Early blight', 'اللفحة المبكرة', 'fungal', true,
   'Sanitation, dry foliage, rotation, balanced feeding; a registered protectant fungicide if pressure is high. Confirm the Egyptian label dose with an agronomist.',
   'نظافة وتجفيف الورق ودورة وتسميد متوازن؛ ومبيد فطري وقائي مسجّل لو الضغط عالي. أكّد الجرعة المصرية مع مهندس زراعي.'),
  ('tomato_late_blight', 'Late blight', 'اللفحة المتأخرة', 'oomycete', true,
   'Act before/at first signs with a registered protectant + systemic programme for oomycetes; destroy infected plants. Timing is critical — confirm the Egyptian label dose with an agronomist.',
   'اتحرّك قبل/مع أول علامة ببرنامج وقائي + جهازي مسجّل للعفن المائي؛ واعدم النباتات المصابة. التوقيت حاسم — أكّد الجرعة المصرية مع مهندس زراعي.'),
  ('tomato_leaf_mold', 'Leaf mold', 'العفن الورقي', 'fungal', true,
   'First lower humidity and improve airflow; a registered protectant fungicide if it persists. Confirm the Egyptian label dose with an agronomist.',
   'الأول قلّل الرطوبة وحسّن التهوية؛ ومبيد فطري وقائي مسجّل لو استمر. أكّد الجرعة المصرية مع مهندس زراعي.'),
  ('septoria_leaf_spot_tomato', 'Septoria leaf spot', 'تبقّع السبتوريا', 'fungal', true,
   'Remove lowest spotted leaves, base-water, mulch, rotate; a registered protectant fungicide at first spots. Confirm the Egyptian label dose with an agronomist.',
   'شيل الورق السفلي المبقّع، واروي من تحت، وغطّي الأرض، ودوّر؛ ومبيد فطري وقائي مسجّل من أول البقع. أكّد الجرعة المصرية مع مهندس زراعي.'),
  ('tomato_spider_mites', 'Spider mites (two-spotted)', 'العنكبوت الأحمر', 'mite', true,
   'A pest, not a disease: wash dust, keep plants watered, protect predators; a registered MITICIDE if it spreads — not a fungicide. Confirm the Egyptian label dose with an agronomist.',
   'آفة مش مرض: اغسل التراب وحافظ على الري واحمِ الأعداء الطبيعية؛ وأكاروسيد مسجّل لو انتشر — مش مبيد فطري. أكّد الجرعة المصرية مع مهندس زراعي.'),
  ('tomato_target_spot', 'Target spot', 'التبقّع الهدفي', 'fungal', true,
   'Airflow, no overhead watering, remove debris, rotate; a registered protectant fungicide at first spots. Look-alikes share evidence — confirm the diagnosis and dose with an agronomist.',
   'تهوية وبعد عن الري من فوق وشيل البقايا ودورة؛ ومبيد فطري وقائي مسجّل من أول البقع. الأمراض الشبيهة بتتشارك الدليل — أكّد التشخيص والجرعة مع مهندس زراعي.'),
  ('tomato_yellow_leaf_curl_virus', 'Yellow leaf curl virus', 'فيروس تجعّد واصفرار الأوراق', 'viral', false,
   'No chemical cures the virus. Control the whitefly vector (traps, nets, rotated insecticides), remove infected plants, use resistant seed. Confirm any insecticide + Egyptian dose with an agronomist.',
   'مفيش كيماوي بيشفي الفيروس. كافح الذبابة البيضا (مصايد، شبك، تبديل مبيدات)، وشيل الزرع المصاب، واستخدم بذرة مقاومة. أكّد أي مبيد + الجرعة المصرية مع مهندس زراعي.'),
  ('tomato_mosaic_virus', 'Mosaic virus', 'فيروس موزاييك الطماطم', 'viral', false,
   'No chemical cures the virus. Control is hygiene: disinfect hands/tools, remove infected plants, resistant/certified seed, no tobacco near the crop.',
   'مفيش كيماوي بيشفي الفيروس. المكافحة نظافة: تطهير الإيدين والأدوات، وشيل الزرع المصاب، وبذرة مقاومة/معتمدة، ومنع الدخان جنب الزرع.'),
  ('healthy', 'No disease signs detected', 'مفيش علامات مرض', 'none', true,
   'No treatment needed. Maintain balanced irrigation, field sanitation, and routine scouting.',
   'مفيش علاج لازم. حافظ على ري متوازن ونظافة الحقل وكشف دوري.')
on conflict (key) do update set
  name_en = excluded.name_en, name_ar = excluded.name_ar,
  cause = excluded.cause, curable = excluded.curable,
  treatment_note_en = excluded.treatment_note_en, treatment_note_ar = excluded.treatment_note_ar,
  updated_at = now();
