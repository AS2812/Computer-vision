create type public.validation_level as enum ('validated', 'experimental', 'sample-data');
create type public.analysis_status as enum ('queued', 'processing', 'complete', 'failed');

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null,
  locale text not null default 'ar',
  created_at timestamptz not null default now()
);

create table public.farms (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  location text,
  created_at timestamptz not null default now()
);

create table public.missions (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  farm_id uuid not null references public.farms(id) on delete cascade,
  name text not null,
  captured_at timestamptz,
  created_at timestamptz not null default now()
);

create table public.uploaded_assets (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  mission_id uuid not null references public.missions(id) on delete cascade,
  storage_path text not null,
  mime_type text not null,
  created_at timestamptz not null default now()
);

create table public.analysis_runs (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  asset_id uuid references public.uploaded_assets(id) on delete cascade,
  status public.analysis_status not null default 'queued',
  provider text,
  processing_ms integer,
  peak_memory_mb numeric,
  created_at timestamptz not null default now()
);

create table public.feature_results (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  analysis_id uuid not null references public.analysis_runs(id) on delete cascade,
  feature text not null,
  level public.validation_level not null,
  score numeric not null check (score between 0 and 1),
  confidence numeric not null check (confidence between 0 and 1),
  value jsonb not null,
  evidence jsonb not null default '[]'::jsonb,
  limitation text,
  created_at timestamptz not null default now()
);

create table public.recommendations (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  analysis_id uuid not null references public.analysis_runs(id) on delete cascade,
  body_ar text not null,
  body_en text not null,
  reviewed boolean not null default false,
  created_at timestamptz not null default now()
);

create table public.alerts (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  analysis_id uuid not null references public.analysis_runs(id) on delete cascade,
  severity text not null check (severity in ('info', 'warning', 'critical')),
  message text not null,
  created_at timestamptz not null default now()
);

create table public.reports (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  analysis_id uuid not null references public.analysis_runs(id) on delete cascade,
  format text not null check (format in ('pdf', 'csv')),
  storage_path text not null,
  created_at timestamptz not null default now()
);

create table public.model_versions (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  version text not null,
  checksum text not null,
  metrics jsonb not null default '{}'::jsonb,
  limitations jsonb not null default '[]'::jsonb,
  approved boolean not null default false,
  created_at timestamptz not null default now(),
  unique (name, version)
);

create table public.knowledge_articles (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  title_ar text not null,
  title_en text not null,
  body_ar text not null,
  body_en text not null,
  reviewed boolean not null default false,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.farms enable row level security;
alter table public.missions enable row level security;
alter table public.uploaded_assets enable row level security;
alter table public.analysis_runs enable row level security;
alter table public.feature_results enable row level security;
alter table public.recommendations enable row level security;
alter table public.alerts enable row level security;
alter table public.reports enable row level security;
alter table public.model_versions enable row level security;
alter table public.knowledge_articles enable row level security;

create policy "profiles own rows" on public.profiles for all using (auth.uid() = id) with check (auth.uid() = id);
create policy "farms own rows" on public.farms for all using (auth.uid() = owner_id) with check (auth.uid() = owner_id);
create policy "missions own rows" on public.missions for all using (auth.uid() = owner_id) with check (auth.uid() = owner_id);
create policy "assets own rows" on public.uploaded_assets for all using (auth.uid() = owner_id) with check (auth.uid() = owner_id);
create policy "analyses own rows" on public.analysis_runs for all using (auth.uid() = owner_id) with check (auth.uid() = owner_id);
create policy "features own rows" on public.feature_results for all using (auth.uid() = owner_id) with check (auth.uid() = owner_id);
create policy "recommendations own rows" on public.recommendations for all using (auth.uid() = owner_id) with check (auth.uid() = owner_id);
create policy "alerts own rows" on public.alerts for all using (auth.uid() = owner_id) with check (auth.uid() = owner_id);
create policy "reports own rows" on public.reports for all using (auth.uid() = owner_id) with check (auth.uid() = owner_id);
create policy "approved models readable" on public.model_versions for select using (approved);
create policy "reviewed knowledge readable" on public.knowledge_articles for select using (reviewed);

insert into storage.buckets (id, name, public, file_size_limit)
values
  ('mission-images', 'mission-images', false, 41943040),
  ('analysis-reports', 'analysis-reports', false, 10485760)
on conflict (id) do nothing;

create policy "users manage mission images" on storage.objects for all
using (bucket_id = 'mission-images' and (storage.foldername(name))[1] = auth.uid()::text)
with check (bucket_id = 'mission-images' and (storage.foldername(name))[1] = auth.uid()::text);

create policy "users manage reports" on storage.objects for all
using (bucket_id = 'analysis-reports' and (storage.foldername(name))[1] = auth.uid()::text)
with check (bucket_id = 'analysis-reports' and (storage.foldername(name))[1] = auth.uid()::text);
