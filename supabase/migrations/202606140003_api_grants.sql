grant usage on schema public to anon, authenticated, service_role;

grant select, insert, update, delete on table
  public.profiles,
  public.farms,
  public.missions,
  public.uploaded_assets,
  public.analysis_runs,
  public.feature_results,
  public.recommendations,
  public.alerts,
  public.reports
to authenticated, service_role;

grant select on table
  public.model_versions,
  public.knowledge_articles
to anon, authenticated, service_role;

grant insert, update, delete on table
  public.model_versions,
  public.knowledge_articles
to service_role;

grant usage, select on all sequences in schema public to authenticated, service_role;

alter default privileges in schema public grant all on tables to service_role;
alter default privileges in schema public grant usage, select on sequences to service_role;
