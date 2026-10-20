-- ============================================================================
-- ElderLife AI — KPI definition catalogue as a database view
--
-- Target engine: PostgreSQL 14+.
--
-- Why a view of text?
-- -------------------
-- The KPI *definitions* (numerator, denominator, missing-data handling) live in
-- `backend/app/services/kpi_definitions.py`. Putting the same definitions in the
-- database lets a Power BI report show, next to each number, exactly what that
-- number means — so a viewer cannot read a KPI without also seeing its caveats.
--
-- The descriptions below are byte-for-byte copies of the Python catalogue.
-- `analytics/export_analytics.py --check-kpis` fails if the two ever diverge,
-- which is what keeps this view honest rather than decorative.
-- ============================================================================

DROP VIEW IF EXISTS analytics_kpi_definitions CASCADE;
CREATE VIEW analytics_kpi_definitions AS
SELECT * FROM (VALUES
    (
        'alert_acknowledgement_rate',
        'Alert acknowledgement rate',
        'ratio',
        'Alerts created in the window whose acknowledged_at is not null.',
        'All alerts created in the window, regardless of status.',
        'Alerts with a null acknowledged_at count toward the denominator and not the numerator. They are never excluded, because excluding them would inflate the rate.',
        'A dismissed alert still counts as acknowledged for this KPI if acknowledged_at is set.'
    ),
    (
        'alert_median_ack_seconds',
        'Median time to acknowledge an alert',
        'seconds',
        'For each acknowledged alert, the seconds between created_at and acknowledged_at; the median of those values.',
        'Alerts created in the window with a non-null acknowledged_at.',
        'Alerts with a null acknowledged_at are excluded from the median and reported separately as `excluded_missing`. The KPI also reports the excluded count so a high median cannot hide a large unacknowledged tail.',
        'Median, not mean: a single very late acknowledgement should not distort the picture.'
    ),
    (
        'alert_resolution_rate',
        'Alert resolution rate',
        'ratio',
        'Alerts created in the window whose status is ''resolved'' (resolved_at not null).',
        'All alerts created in the window.',
        'Unresolved alerts count in the denominator only. Alerts still open are not treated as failures — they may simply not have had time yet, which is why the date range must always accompany this number.',
        ''
    ),
    (
        'high_priority_alert_count',
        'High-priority alert count',
        'count',
        'Alerts with severity in (''high'', ''critical'') created in the window.',
        'Not applicable — this is a count, not a ratio.',
        'No exclusion is needed: the alerts.severity CHECK constraint means only the five known severity levels can be stored, so an unrecognised value cannot enter the table and cannot skew this count.',
        'Counts operational priority, which is not the same as validated medical risk.'
    ),
    (
        'checkin_completion_rate',
        'Check-in completion rate',
        'ratio',
        'Check-ins performed in the window whose status is ''taken''.',
        'Check-ins in the window whose status is one of (''taken'', ''missed'', ''skipped'') — that is, resolved outcomes.',
        'Check-ins still in status ''scheduled'' or ''cancelled'' are excluded from both parts and reported as `excluded_pending`, because they are not yet a completed or failed outcome.',
        ''
    ),
    (
        'medication_adherence_rate',
        'Medication adherence rate',
        'ratio',
        'Medication dose logs in the window whose status is ''taken''.',
        'Medication dose logs in the window whose status is one of (''taken'', ''missed'', ''skipped'').',
        'Doses never logged at all cannot be counted and are therefore NOT included; this KPI measures adherence among *logged* doses and must always be read with the logged-dose count beside it. It cannot prove that an unlogged dose was not taken.',
        ''
    ),
    (
        'care_plan_adherence_rate',
        'Care-plan adherence rate',
        'ratio',
        'Active care-plan items in the window with at least one matching positive outcome (a taken dose or a taken check-in).',
        'Active, actionable care-plan items (kind medication or checkin) belonging to active care plans whose period overlaps the window.',
        'Plan items of kind ''note'' are excluded from both parts: a note is documentation, not an action that can be adhered to. Items of kind ''reminder'' are also excluded, because reminders have no occurrence log yet and so cannot be measured.',
        ''
    ),
    (
        'model_metric_coverage',
        'Model-run metric coverage',
        'ratio',
        'Finished model runs in the window whose metrics_json is not null.',
        'Model runs in the window whose status is ''succeeded'' or ''failed''.',
        'Runs still ''pending'' or ''running'' are excluded from both parts. This KPI measures whether runs *record* metrics; it says nothing about whether those metrics are good.',
        'This KPI deliberately reports only coverage/availability of metrics. Model quality metrics (precision/recall/F1) are produced by the model evaluation pipeline, never invented here.'
    )
) AS t(
    kpi_key,
    kpi_name,
    unit,
    numerator_description,
    denominator_description,
    missing_data_handling,
    notes
);

COMMENT ON VIEW analytics_kpi_definitions IS
    'The formal definition of every KPI: numerator, denominator, and missing-data handling. Mirrors backend/app/services/kpi_definitions.py; verified consistent by analytics/export_analytics.py --check-kpis.';
