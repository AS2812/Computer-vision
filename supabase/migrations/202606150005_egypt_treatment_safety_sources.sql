update public.treatment_rule_versions
set active = false
where active;

insert into public.treatment_rule_versions (
  rule_key, version, disease_class, rule, sources, review_status, active
)
select
  'disease-class-' || disease_class,
  'egypt-safety-baseline-2026-06-15',
  disease_class,
  jsonb_build_object(
    'non_chemical_first', true,
    'requires_current_egyptian_apc_registration', true,
    'requires_egyptian_agricultural_engineer', true,
    'blocks_brand_invention', true,
    'blocks_low_confidence_chemical_advice_without_confirmation', true,
    'submitted_confirmation_is_not_independently_authenticated', true
  ),
  jsonb_build_array(
    'https://www1.apc.gov.eg/en/search.aspx',
    'https://www.apc.gov.eg/EN/PesticidesRegistration.aspx',
    'https://www.qcap-egypt.com/'
  ),
  'internal-safety-baseline',
  true
from unnest(array['fungal', 'bacterial', 'viral', 'insect', 'nutrient', 'abiotic', 'unknown']) disease_class
on conflict (rule_key, version) do update
set
  rule = excluded.rule,
  sources = excluded.sources,
  review_status = excluded.review_status,
  active = excluded.active;
