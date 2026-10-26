ALTER TABLE "buildings" ADD COLUMN "address" text DEFAULT '' NOT NULL;--> statement-breakpoint
ALTER TABLE "buildings" ADD COLUMN "note" jsonb;