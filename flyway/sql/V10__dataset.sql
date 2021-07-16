ALTER TABLE workflow ADD COLUMN dataset_readme_md TEXT NOT NULL DEFAULT '';
COMMENT ON COLUMN workflow.dataset_readme_md IS
  'Markdown to be published the next time the dataset is published. Renderer ignores this and refers to render queue.';

ALTER TABLE tab ADD COLUMN is_in_dataset BOOLEAN NOT NULL DEFAULT FALSE;
COMMENT ON COLUMN tab.is_in_dataset IS
  'True iff the next dataset we publish should include this tab. Renderer ignores this and refers to render queue.';
