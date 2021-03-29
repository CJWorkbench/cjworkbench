ALTER TABLE workflow ADD COLUMN secret_id VARCHAR NOT NULL DEFAULT '';
CREATE UNIQUE INDEX unique_workflow_secret_id ON workflow (secret_id) WHERE secret_id <> '';
