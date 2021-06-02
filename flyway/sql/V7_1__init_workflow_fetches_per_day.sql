-- Deploy this after all frontends are updating workflow.fetches_per_day.
-- It'll set every workflow to the correct value.
--
-- Tested an equivalent SELECT on production, 2021-06-02 => took ~1s for
-- 90k workflows.
UPDATE workflow
SET fetches_per_day = (
  SELECT COALESCE(SUM(86400.0 / step.update_interval), 0.0)
  FROM step
  WHERE NOT step.is_deleted
    AND step.tab_id IN (
      SELECT id
      FROM tab
      WHERE NOT tab.is_deleted
        AND tab.workflow_id = workflow.id
    )
)
