-- 002-paired-scenarios.sql
-- Pairing support: capacity_scenarios.candidate_windows holds the candidate counter count.
-- NULL means a legacy single-plan scenario; both values share one profile and one seed.
-- Existing deployments must apply this ALTER before starting the new backend/worker.
ALTER TABLE capacity_scenarios ADD COLUMN candidate_windows INT NULL AFTER windows;

-- Archives created before this migration keep the old replication-only CSV layout;
-- their simulation_runs.result has no "mode" key and is read as a single-plan run.
