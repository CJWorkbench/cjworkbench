ALTER TABLE workflow ADD COLUMN dataset_readme_md TEXT NOT NULL DEFAULT '';
COMMENT ON workflow.dataset_readme_md IS 'Markdown to be published the next time the dataset is published. This powers the user interface only: the dataset is generated from the value in the render queue, _not_ the value in the database.';

ALTER TABLE tab ADD COLUMN is_in_dataset BOOLEAN NOT NULL DEFAULT FALSE;
COMMENT ON tab.is_in_dataset IS 'True iff the next dataset we publish should include this tab. This powers the user interface only: the dataset is generated from the values in the render queue, _not_ the value in the database.';
