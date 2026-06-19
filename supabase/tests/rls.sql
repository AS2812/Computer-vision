begin;
select plan(38);

select has_table('public', 'profiles', 'profiles exists');
select has_table('public', 'farms', 'farms exists');
select has_table('public', 'missions', 'missions exists');
select has_table('public', 'uploaded_assets', 'uploaded_assets exists');
select has_table('public', 'analysis_runs', 'analysis_runs exists');
select has_table('public', 'feature_results', 'feature_results exists');
select has_table('public', 'recommendations', 'recommendations exists');
select has_table('public', 'alerts', 'alerts exists');
select has_table('public', 'reports', 'reports exists');
select has_table('public', 'model_versions', 'model_versions exists');
select has_table('public', 'knowledge_articles', 'knowledge_articles exists');
select has_table('public', 'crop_cases', 'crop cases exists');
select has_table('public', 'case_observations', 'case observations exists');
select has_table('public', 'case_diagnoses', 'case diagnoses exists');
select has_table('public', 'case_assets', 'case assets exists');
select has_table('public', 'case_reports', 'case reports exists');
select has_table('public', 'treatment_rule_versions', 'treatment rule versions exists');
select has_table('public', 'case_treatment_plans', 'case treatment plans exists');

select policies_are('public', 'profiles', array['profiles own rows'], 'profiles use owner policy');
select policies_are('public', 'farms', array['farms own rows'], 'farms use owner policy');
select policies_are('public', 'missions', array['missions own rows'], 'missions use owner policy');
select policies_are('public', 'uploaded_assets', array['assets own rows'], 'assets use owner policy');
select policies_are('public', 'analysis_runs', array['analyses own rows'], 'analysis runs use owner policy');
select policies_are('public', 'feature_results', array['features own rows'], 'feature results use owner policy');
select policies_are('public', 'recommendations', array['recommendations own rows'], 'recommendations use owner policy');
select policies_are('public', 'alerts', array['alerts own rows'], 'alerts use owner policy');
select policies_are('public', 'reports', array['reports own rows'], 'reports use owner policy');
select policies_are('public', 'model_versions', array['approved models readable'], 'only approved models are readable');
select policies_are('public', 'knowledge_articles', array['reviewed knowledge readable'], 'only reviewed knowledge is readable');
select policies_are('public', 'crop_cases', array['crop cases own rows'], 'crop cases use owner policy');
select policies_are('public', 'case_observations', array['case observations own rows'], 'case observations use owner policy');
select policies_are('public', 'case_diagnoses', array['case diagnoses own rows'], 'case diagnoses use owner policy');
select policies_are('public', 'case_assets', array['case assets own rows'], 'case assets use owner policy');
select policies_are('public', 'case_reports', array['case reports own rows'], 'case reports use owner policy');
select policies_are('public', 'treatment_rule_versions', array['active treatment rules readable'], 'only active treatment rules are readable');
select policies_are('public', 'case_treatment_plans', array['case treatment plans own rows'], 'case treatment plans use owner policy');

select results_eq(
  $$select count(*)::bigint from public.treatment_rule_versions where active$$,
  array[7::bigint],
  'seven disease-class safety baselines are active'
);

select results_eq(
  $$select count(*)::bigint from public.treatment_rule_versions where review_status = 'agronomist-reviewed'$$,
  array[0::bigint],
  'internal safety baselines are not falsely marked agronomist-reviewed'
);

select * from finish();
rollback;
