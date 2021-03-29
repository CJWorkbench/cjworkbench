-- Existing Django code tries to write "example", so we have to allow it.
-- New Django code will ignore the column. So set a default.
ALTER TABLE workflow ALTER COLUMN example SET DEFAULT FALSE;
