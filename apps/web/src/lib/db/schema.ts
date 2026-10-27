import { boolean, index, integer, jsonb, pgTable, real, text, timestamp, uniqueIndex, uuid } from "drizzle-orm/pg-core";
import type { BuildingNote, Report, WorkerStage } from "../report-types";

export type CommunityType = "HOA" | "Condo" | "Home" | "Commercial";
export type EaveMode = "unknown" | "known" | "none"; // "none": no overhang (flat roof, parapet)
export type FixStatus = "open" | "progress" | "fixed" | "verified" | "wontfix";
export type Responsibility = "HOA" | "Owner" | "Unclear";
export interface FixNote {
  text: string;
  at: string; // ISO timestamp
  by: string;
}

export const communities = pgTable("communities", {
  id: uuid("id").primaryKey().defaultRandom(),
  name: text("name").notNull(),
  type: text("type").$type<CommunityType>().notNull().default("HOA"),
  place: text("place").notNull().default(""),
  rulePack: text("rule_pack").notNull().default("us-ca"),
  includeProposed: boolean("include_proposed").notNull().default(true),
  isSample: boolean("is_sample").notNull().default(false),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export const buildings = pgTable(
  "buildings",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    communityId: uuid("community_id")
      .notNull()
      .references(() => communities.id, { onDelete: "cascade" }),
    label: text("label").notNull(),
    units: text("units").notNull().default(""),
    address: text("address").notNull().default(""),
    // Address research note (worker POST /research): jurisdiction, hazard zone, law, recent fires.
    note: jsonb("note").$type<BuildingNote>(),
    eaveMode: text("eave_mode").$type<EaveMode>().notNull().default("unknown"),
    eaveFt: real("eave_ft"),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("buildings_community_idx").on(t.communityId)],
);

export const scans = pgTable(
  "scans",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    buildingId: uuid("building_id")
      .notNull()
      .references(() => buildings.id, { onDelete: "cascade" }),
    workerScanId: text("worker_scan_id"),
    status: text("status").notNull().default("queued"), // queued | processing | done | failed
    stage: text("stage"),
    progress: real("progress").notNull().default(0),
    stages: jsonb("stages").$type<WorkerStage[]>(),
    error: text("error"),
    report: jsonb("report").$type<Report>(),
    isSample: boolean("is_sample").notNull().default(false),
    createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  },
  (t) => [index("scans_building_idx").on(t.buildingId, t.createdAt)],
);

export const fixTasks = pgTable(
  "fix_tasks",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    buildingId: uuid("building_id")
      .notNull()
      .references(() => buildings.id, { onDelete: "cascade" }),
    ruleId: text("rule_id").notNull(),
    title: text("title").notNull().default(""),
    responsibility: text("responsibility").$type<Responsibility>().notNull().default("Unclear"),
    required: boolean("required").notNull().default(false),
    status: text("status").$type<FixStatus>().notNull().default("open"),
    owner: text("owner").notNull().default(""),
    notes: jsonb("notes").$type<FixNote[]>().notNull().default([]),
    sourceScanId: uuid("source_scan_id"),
    updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
    priority: integer("priority").notNull().default(99),
  },
  (t) => [uniqueIndex("fix_tasks_building_rule_idx").on(t.buildingId, t.ruleId)],
);

export type Community = typeof communities.$inferSelect;
export type Building = typeof buildings.$inferSelect;
export type Scan = typeof scans.$inferSelect;
export type FixTask = typeof fixTasks.$inferSelect;
