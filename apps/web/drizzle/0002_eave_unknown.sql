ALTER TABLE "buildings" ALTER COLUMN "eave_mode" SET DEFAULT 'unknown';--> statement-breakpoint
UPDATE "buildings" SET "eave_mode" = 'unknown' WHERE "eave_mode" = 'video';