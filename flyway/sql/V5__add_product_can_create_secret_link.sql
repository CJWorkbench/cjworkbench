ALTER TABLE product ADD COLUMN can_create_secret_link BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE product ALTER COLUMN can_create_secret_link DROP DEFAULT;
