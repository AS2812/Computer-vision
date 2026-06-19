alter table public.case_assets
drop constraint if exists case_assets_view_type_check;

alter table public.case_assets
add constraint case_assets_view_type_check check (
  view_type in (
    'close_up_leaf', 'whole_plant', 'leaf_underside', 'fruit',
    'stem', 'root', 'healthy_comparison', 'diagnosis_confirmation', 'other'
  )
);
