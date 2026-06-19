create table public.treatment_rule_versions (
  id uuid primary key default gen_random_uuid(),
  rule_key text not null,
  version text not null,
  disease_class text not null check (
    disease_class in ('fungal', 'bacterial', 'viral', 'insect', 'nutrient', 'abiotic', 'unknown')
  ),
  rule jsonb not null,
  sources jsonb not null default '[]'::jsonb,
  review_status text not null check (
    review_status in ('internal-safety-baseline', 'agronomist-reviewed', 'retired')
  ),
  active boolean not null default false,
  created_at timestamptz not null default now(),
  unique (rule_key, version)
);

create table public.case_treatment_plans (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  case_id uuid not null references public.crop_cases(id) on delete cascade,
  disease_class text not null check (
    disease_class in ('fungal', 'bacterial', 'viral', 'insect', 'nutrient', 'abiotic', 'unknown')
  ),
  rule_version text not null,
  plan jsonb not null,
  updated_at timestamptz not null default now(),
  unique (case_id)
);

alter table public.treatment_rule_versions enable row level security;
alter table public.case_treatment_plans enable row level security;

create policy "active treatment rules readable" on public.treatment_rule_versions
for select using (active);

create policy "case treatment plans own rows" on public.case_treatment_plans
for all using (auth.uid() = owner_id) with check (auth.uid() = owner_id);

grant select on table public.treatment_rule_versions to anon, authenticated, service_role;
grant insert, update, delete on table public.treatment_rule_versions to service_role;
grant select, insert, update, delete on table public.case_treatment_plans to authenticated, service_role;

insert into public.treatment_rule_versions (
  rule_key, version, disease_class, rule, sources, review_status, active
)
select
  'disease-class-' || disease_class,
  'internal-safety-baseline-2026-06-15',
  disease_class,
  jsonb_build_object(
    'non_chemical_first', true,
    'requires_local_label_verification', true,
    'requires_agricultural_engineer', true,
    'blocks_brand_invention', true,
    'blocks_low_confidence_chemical_advice', true
  ),
  jsonb_build_array('docs/AGROVISION_DECISION_SUPPORT_ARCHITECTURE.md'),
  'internal-safety-baseline',
  true
from unnest(array['fungal', 'bacterial', 'viral', 'insect', 'nutrient', 'abiotic', 'unknown']) disease_class;
