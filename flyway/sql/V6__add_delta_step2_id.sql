ALTER TABLE delta
  ADD COLUMN step2_id INT DEFAULT NULL REFERENCES step (id),
  DROP CONSTRAINT delta_command_name_valid,
  ADD CONSTRAINT delta_command_name_valid CHECK (
    command_name IN (
      'AddBlock',
      'AddStep',
      'AddTab',
      'DeleteBlock',
      'DeleteStep',
      'DeleteTab',
      'DuplicateTab',
      'InitWorkflow',
      'ReorderBlocks',
      'ReorderSteps',
      'ReorderTabs',
      'ReplaceStep',
      'SetBlockMarkdown',
      'SetStepDataVersion',
      'SetStepNote',
      'SetStepParams',
      'SetTabName',
      'SetWorkflowTitle'
    )
  );
