CREATE TYPE acl_role AS ENUM ('editor', 'viewer', 'report-viewer');

ALTER TABLE acl_entry
  ADD COLUMN role acl_role NOT NULL DEFAULT 'viewer'::acl_role;
UPDATE acl_entry SET role = 'editor' WHERE can_edit;
ALTER TABLE acl_entry
  DROP COLUMN can_edit;
