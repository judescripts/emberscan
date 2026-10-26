CREATE TABLE "buildings" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"community_id" uuid NOT NULL,
	"label" text NOT NULL,
	"units" text DEFAULT '' NOT NULL,
	"eave_mode" text DEFAULT 'video' NOT NULL,
	"eave_ft" real,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "communities" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" text NOT NULL,
	"type" text DEFAULT 'HOA' NOT NULL,
	"place" text DEFAULT '' NOT NULL,
	"rule_pack" text DEFAULT 'us-ca' NOT NULL,
	"include_proposed" boolean DEFAULT true NOT NULL,
	"is_sample" boolean DEFAULT false NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "fix_tasks" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"building_id" uuid NOT NULL,
	"rule_id" text NOT NULL,
	"title" text DEFAULT '' NOT NULL,
	"responsibility" text DEFAULT 'Unclear' NOT NULL,
	"required" boolean DEFAULT false NOT NULL,
	"status" text DEFAULT 'open' NOT NULL,
	"owner" text DEFAULT '' NOT NULL,
	"notes" jsonb DEFAULT '[]'::jsonb NOT NULL,
	"source_scan_id" uuid,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"priority" integer DEFAULT 99 NOT NULL
);
--> statement-breakpoint
CREATE TABLE "scans" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"building_id" uuid NOT NULL,
	"worker_scan_id" text,
	"status" text DEFAULT 'queued' NOT NULL,
	"stage" text,
	"progress" real DEFAULT 0 NOT NULL,
	"stages" jsonb,
	"error" text,
	"report" jsonb,
	"is_sample" boolean DEFAULT false NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "buildings" ADD CONSTRAINT "buildings_community_id_communities_id_fk" FOREIGN KEY ("community_id") REFERENCES "public"."communities"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "fix_tasks" ADD CONSTRAINT "fix_tasks_building_id_buildings_id_fk" FOREIGN KEY ("building_id") REFERENCES "public"."buildings"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "scans" ADD CONSTRAINT "scans_building_id_buildings_id_fk" FOREIGN KEY ("building_id") REFERENCES "public"."buildings"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "buildings_community_idx" ON "buildings" USING btree ("community_id");--> statement-breakpoint
CREATE UNIQUE INDEX "fix_tasks_building_rule_idx" ON "fix_tasks" USING btree ("building_id","rule_id");--> statement-breakpoint
CREATE INDEX "scans_building_idx" ON "scans" USING btree ("building_id","created_at");