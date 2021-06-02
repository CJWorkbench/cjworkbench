-- Fix the values from the previous update.
UPDATE workflow
SET fetches_per_day = (
  SELECT COALESCE(SUM(86400.0 / step.update_interval), 0.0)
  FROM step
  WHERE NOT step.is_deleted
    AND step.auto_update_data
    AND step.tab_id IN (
      SELECT id
      FROM tab
      WHERE NOT tab.is_deleted
        AND tab.workflow_id = workflow.id
    )
)
