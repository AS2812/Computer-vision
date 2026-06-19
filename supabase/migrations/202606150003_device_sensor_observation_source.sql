alter table public.case_observations
  drop constraint if exists case_observations_source_check;

alter table public.case_observations
  add constraint case_observations_source_check
  check (
    source in (
      'farmer_answer',
      'image_model',
      'image_measurement',
      'device_sensor',
      'reviewed_rule',
      'expert',
      'lab'
    )
  );
