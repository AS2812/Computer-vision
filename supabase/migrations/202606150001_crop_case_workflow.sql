create type public.case_status as enum (
  'draft',
  'collecting_evidence',
  'diagnosis_ready',
  'consulting',
  'protection_ready',
  'treatment_ready',
  'economics_ready',
  'prediction_ready',
  'recommendation_ready',
  'report_ready',
  'needs_expert',
  'closed',
  'failed'
);

create table public.crop_cases (
  id uuid primary key,
  owner_id uuid not null references auth.users(id) on delete cascade,
  farm_id uuid references public.farms(id) on delete set null,
  status public.case_status not null default 'draft',
  crop_type text not null,
  location text not null default '',
  farm_type text check (
    farm_type is null or farm_type in ('open_field', 'greenhouse', 'rooftop', 'home_garden')
  ),
  growth_stage text,
  symptoms jsonb not null default '[]'::jsonb,
  snapshot jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.case_observations (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  case_id uuid not null references public.crop_cases(id) on delete cascade,
  observation_type text not null,
  value jsonb not null,
  source text not null default 'farmer_answer' check (
    source in ('farmer_answer', 'image_model', 'image_measurement', 'reviewed_rule', 'expert', 'lab')
  ),
  updated_at timestamptz not null default now(),
  unique (case_id, observation_type)
);

create table public.case_diagnoses (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  case_id uuid not null references public.crop_cases(id) on delete cascade,
  top_disease text not null,
  confidence numeric not null check (confidence between 0 and 1),
  alternatives jsonb not null default '[]'::jsonb,
  evidence jsonb not null default '[]'::jsonb,
  missing_info jsonb not null default '[]'::jsonb,
  source text not null default 'image_model' check (
    source in ('image_model', 'reviewed_rule', 'expert', 'lab')
  ),
  updated_at timestamptz not null default now(),
  unique (case_id)
);

create table public.case_assets (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  case_id uuid not null references public.crop_cases(id) on delete cascade,
  storage_path text not null,
  mime_type text not null,
  view_type text not null default 'close_up_leaf' check (
    view_type in (
      'close_up_leaf', 'whole_plant', 'leaf_underside', 'fruit',
      'stem', 'root', 'healthy_comparison', 'other'
    )
  ),
  model_evidence jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table public.case_reports (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  case_id uuid not null references public.crop_cases(id) on delete cascade,
  system_output jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (case_id)
);

create index crop_cases_owner_updated_idx on public.crop_cases (owner_id, updated_at desc);
create index case_observations_case_idx on public.case_observations (case_id);
create index case_assets_case_idx on public.case_assets (case_id);

alter table public.crop_cases enable row level security;
alter table public.case_observations enable row level security;
alter table public.case_diagnoses enable row level security;
alter table public.case_assets enable row level security;
alter table public.case_reports enable row level security;

create policy "crop cases own rows" on public.crop_cases
for all using (auth.uid() = owner_id) with check (auth.uid() = owner_id);

create policy "case observations own rows" on public.case_observations
for all using (auth.uid() = owner_id) with check (auth.uid() = owner_id);

create policy "case diagnoses own rows" on public.case_diagnoses
for all using (auth.uid() = owner_id) with check (auth.uid() = owner_id);

create policy "case assets own rows" on public.case_assets
for all using (auth.uid() = owner_id) with check (auth.uid() = owner_id);

create policy "case reports own rows" on public.case_reports
for all using (auth.uid() = owner_id) with check (auth.uid() = owner_id);

insert into storage.buckets (id, name, public, file_size_limit)
values ('case-images', 'case-images', false, 41943040)
on conflict (id) do nothing;

create policy "users manage case images" on storage.objects for all
using (bucket_id = 'case-images' and (storage.foldername(name))[1] = auth.uid()::text)
with check (bucket_id = 'case-images' and (storage.foldername(name))[1] = auth.uid()::text);

grant select, insert, update, delete on table
  public.crop_cases,
  public.case_observations,
  public.case_diagnoses,
  public.case_assets,
  public.case_reports
to authenticated, service_role;

grant usage, select on all sequences in schema public to authenticated, service_role;
