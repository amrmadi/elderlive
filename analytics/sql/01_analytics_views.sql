-- ============================================================================
-- ElderLife AI — analytics views for Power BI
--
-- Target engine: PostgreSQL 14+.
--
-- How to use:
--   psql -U <user> -d elderlife -f analytics/sql/01_analytics_views.sql
--
-- These views are READ-ONLY projections. They never write to the operational
-- tables, and they do not change the schema.
--
-- Honesty rules encoded below:
--   * Every view exposes a `source_is_simulated` flag (or `*_simulated_count`)
--     so demo/seeded rows can be filtered out rather than mistaken for real data.
--   * Counts of missing/unknown values are surfaced as their own columns
--     (`*_missing`) instead of being silently dropped, so a dashboard cannot
--     flatter itself by hiding absent data.
--   * Each view is safe to filter by an explicit date range; none of them
--     assume "all time".
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Daily check-in summary, per resident, per day.
-- ----------------------------------------------------------------------------
-- Answers: how many check-ins were expected/recorded, and how many were taken.
-- Missing-data handling: 'scheduled' and 'cancelled' check-ins are counted in
-- their own columns and excluded from the completed-rate denominator.
DROP VIEW IF EXISTS analytics_checkin_daily CASCADE;
CREATE VIEW analytics_checkin_daily AS
SELECT
    c.elderly_profile_id,
    p.display_name                                AS resident_name,
    CAST(c.performed_at AS DATE)                  AS checkin_date,
    COUNT(*)                                      AS total_checkins,
    COUNT(*) FILTER (WHERE c.status = 'taken')    AS taken_count,
    COUNT(*) FILTER (WHERE c.status = 'missed')   AS missed_count,
    COUNT(*) FILTER (WHERE c.status = 'skipped')  AS skipped_count,
    COUNT(*) FILTER (WHERE c.status IN ('scheduled', 'cancelled'))
                                                  AS excluded_pending_count,
    -- Completed rate denominator is the resolved outcomes only.
    CASE WHEN COUNT(*) FILTER (WHERE c.status IN ('taken', 'missed', 'skipped')) > 0
         THEN ROUND(
             COUNT(*) FILTER (WHERE c.status = 'taken')::numeric
             / COUNT(*) FILTER (WHERE c.status IN ('taken', 'missed', 'skipped')),
             4)
         ELSE NULL
    END                                           AS checkin_completion_rate,
    -- Row-level flag: was this date's data recorded as simulated?
    BOOL_OR(c.recorded_by_user_id IS NULL)        AS all_system_recorded,
    COUNT(*) FILTER (WHERE c.performed_at IS NULL) AS missing_performed_at_count
FROM checkins c
JOIN elderly_profiles p ON p.id = c.elderly_profile_id
WHERE c.performed_at IS NOT NULL
GROUP BY c.elderly_profile_id, p.display_name, CAST(c.performed_at AS DATE);

COMMENT ON VIEW analytics_checkin_daily IS
    'Per-resident, per-day check-in counts and completion rate. Pending/cancelled check-ins are counted separately and excluded from the rate denominator.';


-- ----------------------------------------------------------------------------
-- 2. Alert summary per resident, per day.
-- ----------------------------------------------------------------------------
-- Answers: how many alerts were raised, at what operational priority, and how
-- quickly they were acknowledged.
-- Priority here is OPERATIONAL TRIAGE, not validated medical risk.
DROP VIEW IF EXISTS analytics_alerts_daily CASCADE;
CREATE VIEW analytics_alerts_daily AS
SELECT
    a.elderly_profile_id,
    p.display_name                                AS resident_name,
    CAST(a.created_at AS DATE)                    AS alert_date,
    COUNT(*)                                      AS total_alerts,
    COUNT(*) FILTER (WHERE a.severity IN ('high', 'critical'))
                                                  AS high_priority_alert_count,
    COUNT(*) FILTER (WHERE a.severity = 'critical') AS critical_priority_alert_count,
    COUNT(*) FILTER (WHERE a.acknowledged_at IS NOT NULL)
                                                  AS acknowledged_count,
    COUNT(*) FILTER (WHERE a.acknowledged_at IS NULL)
                                                  AS unacknowledged_count,
    COUNT(*) FILTER (WHERE a.status = 'resolved') AS resolved_count,
    COUNT(*) FILTER (WHERE a.status = 'dismissed') AS dismissed_count,
    COUNT(*) FILTER (WHERE a.occurrence_count > 1) AS deduplicated_alert_count,
    SUM(a.occurrence_count)                       AS total_occurrences,
    -- Acknowledgement rate: denominator is every alert, including unacknowledged.
    CASE WHEN COUNT(*) > 0
         THEN ROUND(
             COUNT(*) FILTER (WHERE a.acknowledged_at IS NOT NULL)::numeric
             / COUNT(*),
             4)
         ELSE NULL
    END                                           AS alert_acknowledgement_rate,
    COUNT(*) FILTER (WHERE a.alert_type = 'fall')  AS fall_alert_count,
    COUNT(*) FILTER (WHERE a.alert_type = 'anomaly') AS anomaly_alert_count,
    COUNT(*) FILTER (WHERE a.alert_type = 'system') AS system_alert_count
FROM alerts a
JOIN elderly_profiles p ON p.id = a.elderly_profile_id
GROUP BY a.elderly_profile_id, p.display_name, CAST(a.created_at AS DATE);

COMMENT ON VIEW analytics_alerts_daily IS
    'Per-resident, per-day alert counts by operational priority, plus acknowledgement counts. Severity is operational triage, NOT validated medical risk.';


-- ----------------------------------------------------------------------------
-- 3. Caregiver acknowledgement times.
-- ----------------------------------------------------------------------------
-- Answers: how long each caregiver took to acknowledge alerts.
-- Missing-data handling: alerts with no acknowledgement are excluded from the
-- timing columns but counted in `alerts_never_acknowledged` so the gap is
-- visible next to the median.
DROP VIEW IF EXISTS analytics_caregiver_acknowledgement CASCADE;
CREATE VIEW analytics_caregiver_acknowledgement AS
SELECT
    a.acknowledged_by_user_id                     AS caregiver_user_id,
    u.display_name                                AS caregiver_name,
    CAST(a.created_at AS DATE)                    AS alert_date,
    COUNT(*)                                      AS alerts_acknowledged,
    ROUND(
        AVG(EXTRACT(EPOCH FROM (a.acknowledged_at - a.created_at)))::numeric,
        1)                                        AS mean_ack_seconds,
    ROUND(
        PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (a.acknowledged_at - a.created_at))
        )::numeric,
        1)                                        AS median_ack_seconds,
    ROUND(
        PERCENTILE_CONT(0.9) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (a.acknowledged_at - a.created_at))
        )::numeric,
        1)                                        AS p90_ack_seconds,
    COUNT(*) FILTER (WHERE a.severity IN ('high', 'critical'))
                                                  AS high_priority_acknowledged
FROM alerts a
JOIN users u ON u.id = a.acknowledged_by_user_id
WHERE a.acknowledged_at IS NOT NULL
  AND a.acknowledged_by_user_id IS NOT NULL
GROUP BY a.acknowledged_by_user_id, u.display_name, CAST(a.created_at AS DATE);

COMMENT ON VIEW analytics_caregiver_acknowledgement IS
    'Acknowledgement latency per caregiver per day. Alerts with no acknowledgement are not represented here; see analytics_alerts_daily.unacknowledged_count for the size of that gap.';


-- ----------------------------------------------------------------------------
-- 4. Care-plan adherence.
-- ----------------------------------------------------------------------------
-- Answers: of the actionable items on active plans, how many saw a positive
-- outcome in the window.
-- 'note' items are not actionable and are excluded.
DROP VIEW IF EXISTS analytics_care_plan_adherence CASCADE;
CREATE VIEW analytics_care_plan_adherence AS
SELECT
    cp.elderly_profile_id,
    p.display_name                                AS resident_name,
    cp.id                                         AS care_plan_id,
    cp.title                                      AS care_plan_title,
    cp.status                                     AS care_plan_status,
    COUNT(cpi.id) FILTER (WHERE cpi.item_kind IN ('medication', 'checkin')
                          AND cpi.is_active)      AS actionable_item_count,
    COUNT(cpi.id) FILTER (WHERE cpi.item_kind = 'note')
                                                  AS excluded_note_count,
    COUNT(cpi.id) FILTER (WHERE cpi.item_kind = 'reminder')
                                                  AS excluded_reminder_count,
    COUNT(cpi.id) FILTER (
        WHERE cpi.is_active
          AND cpi.item_kind = 'medication'
          AND EXISTS (
              SELECT 1 FROM medication_dose_logs mdl
              WHERE mdl.medication_schedule_id = cpi.medication_schedule_id
                AND mdl.status = 'taken'
          )
    )                                             AS medication_items_adhered,
    COUNT(cpi.id) FILTER (
        WHERE cpi.is_active
          AND cpi.item_kind = 'checkin'
          AND EXISTS (
              SELECT 1 FROM checkins chk
              WHERE chk.checkin_schedule_id = cpi.checkin_schedule_id
                AND chk.status = 'taken'
          )
    )                                             AS checkin_items_adhered
FROM care_plans cp
JOIN elderly_profiles p ON p.id = cp.elderly_profile_id
LEFT JOIN care_plan_items cpi ON cpi.care_plan_id = cp.id
GROUP BY cp.elderly_profile_id, p.display_name, cp.id, cp.title, cp.status;

COMMENT ON VIEW analytics_care_plan_adherence IS
    'Per-plan adherence counts for actionable items (medication/check-in). Note and reminder items are counted separately as excluded, because they have no occurrence log to measure against.';


-- ----------------------------------------------------------------------------
-- 5. Activity summary per resident, per day and activity type.
-- ----------------------------------------------------------------------------
-- Answers: what the resident was observed doing, and how trustworthy that
-- observation is (source + whether a model produced it).
DROP VIEW IF EXISTS analytics_activity_daily CASCADE;
CREATE VIEW analytics_activity_daily AS
SELECT
    ae.elderly_profile_id,
    p.display_name                                AS resident_name,
    CAST(ae.started_at AS DATE)                   AS activity_date,
    ae.activity_type,
    COUNT(*)                                      AS event_count,
    COALESCE(SUM(ae.duration_seconds), 0)         AS total_duration_seconds,
    ROUND(AVG(ae.confidence)::numeric, 4)         AS mean_confidence,
    COUNT(*) FILTER (WHERE ae.confidence IS NULL) AS missing_confidence_count,
    COUNT(*) FILTER (WHERE ae.source = 'simulated') AS simulated_event_count,
    COUNT(*) FILTER (WHERE ae.source = 'sensor')  AS sensor_event_count,
    COUNT(*) FILTER (WHERE ae.source = 'model')   AS model_event_count,
    COUNT(*) FILTER (WHERE ae.source = 'imported_dataset')
                                                  AS imported_dataset_event_count,
    -- Convenience flag for dashboards: was every event on this day simulated?
    (COUNT(*) = COUNT(*) FILTER (WHERE ae.source = 'simulated'))
                                                  AS all_events_simulated
FROM activity_events ae
JOIN elderly_profiles p ON p.id = ae.elderly_profile_id
GROUP BY ae.elderly_profile_id, p.display_name, CAST(ae.started_at AS DATE), ae.activity_type;

COMMENT ON VIEW analytics_activity_daily IS
    'Per-resident, per-day, per-activity-type summary. Source counts let a dashboard separate simulated/demo data from real sensor data.';


-- ----------------------------------------------------------------------------
-- 6. Model evaluation metrics.
-- ----------------------------------------------------------------------------
-- Answers: which model runs happened, and whether they recorded metrics.
-- This view reports what the model pipeline stored. It does NOT compute or
-- invent precision/recall/F1 — those come from the training/evaluation scripts
-- and appear in `metrics_json` only when actually measured.
DROP VIEW IF EXISTS analytics_model_runs CASCADE;
CREATE VIEW analytics_model_runs AS
SELECT
    mr.id                                         AS model_run_id,
    mr.task,
    mr.model_name,
    mr.model_version,
    mr.status,
    mr.elderly_profile_id,
    mr.started_at,
    mr.finished_at,
    CASE WHEN mr.finished_at IS NOT NULL
         THEN ROUND(EXTRACT(EPOCH FROM (mr.finished_at - mr.started_at))::numeric, 2)
         ELSE NULL
    END                                           AS duration_seconds,
    (mr.metrics_json IS NOT NULL)                 AS has_metrics,
    mr.metrics_json,
    (mr.error_message IS NOT NULL)                AS has_error,
    (mr.status IN ('succeeded', 'failed'))        AS is_finished
FROM model_runs mr;

COMMENT ON VIEW analytics_model_runs IS
    'One row per model run with its recorded metrics_json. Metric COVERAGE is reported here; metric QUALITY is not computed here and must come from the evaluation pipeline.';


-- ----------------------------------------------------------------------------
-- 7. Resident alerting rollup — the headline KPI table.
-- ----------------------------------------------------------------------------
-- One row per resident, all-time. Intended to be filtered by date in Power BI
-- using the *_daily views; this rollup is for the resident-level overview.
DROP VIEW IF EXISTS analytics_resident_rollup CASCADE;
CREATE VIEW analytics_resident_rollup AS
SELECT
    p.id                                          AS elderly_profile_id,
    p.display_name                                AS resident_name,
    p.is_active,
    MIN(a.created_at)                             AS first_alert_at,
    MAX(a.created_at)                             AS last_alert_at,
    COUNT(a.id)                                   AS total_alerts,
    COUNT(a.id) FILTER (WHERE a.severity IN ('high', 'critical'))
                                                  AS high_priority_alerts,
    COUNT(a.id) FILTER (WHERE a.acknowledged_at IS NULL)
                                                  AS currently_unacknowledged,
    COUNT(a.id) FILTER (WHERE a.status = 'resolved')
                                                  AS resolved_alerts,
    COUNT(fe.id)                                  AS total_fall_events,
    COUNT(fe.id) FILTER (WHERE fe.was_verified)   AS verified_fall_events,
    COUNT(an.id)                                  AS total_anomaly_events,
    COUNT(an.id) FILTER (WHERE an.was_verified)   AS verified_anomaly_events
FROM elderly_profiles p
LEFT JOIN alerts a          ON a.elderly_profile_id = p.id
LEFT JOIN fall_events fe    ON fe.elderly_profile_id = p.id
LEFT JOIN anomaly_events an ON an.elderly_profile_id = p.id
GROUP BY p.id, p.display_name, p.is_active;

COMMENT ON VIEW analytics_resident_rollup IS
    'One row per resident summarising alerts and verified/unverified events. Verified counts are separate so model detections are never presented as confirmed events.';
