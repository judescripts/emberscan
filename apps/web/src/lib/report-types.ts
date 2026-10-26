// TypeScript mirror of workers/src/emberscan_workers/contracts.py (Report JSON v1).
// Keep in sync with the Python models: they are the seam between pipeline and web.

export type Side = "N" | "E" | "S" | "W" | "roof" | "unknown";
export type Confidence = "high" | "medium" | "low";
export type Method = "marker" | "tape" | "door" | "depth" | "visual";
export type RuleStatus = "pass" | "fail" | "needs-review";
export type RulePackStatus = "adopted" | "proposed" | "guidance";

export interface Range {
  min: number;
  max: number;
}

export interface BBox {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export interface Evidence {
  frame_index: number;
  timestamp_ms: number;
  bbox: BBox;
  image_path?: string | null;
}

export interface Hazard {
  id: string;
  cls: string;
  concept: string;
  track_id: string;
  label: string;
  frames: number[];
  confidence: Confidence;
  sam_confidence?: number | null;
  method: Method;
  distance_ft?: Range | null;
  clearance_ft?: Range | null;
  clearance_to?: string | null;
  height_in?: Range | null;
  zone?: string | null;
  zone_uncertain: boolean;
  side: Side;
  narration?: string | null;
  evidence: Evidence[];
}

export interface RuleResult {
  rule_id: string;
  title: string;
  zone: string;
  rule_status: RulePackStatus;
  status: RuleStatus;
  reason: string;
  hazard_ids: string[];
  citation_url: string;
  citation_label: string;
}

export interface Fix {
  id: string;
  title: string;
  why: string;
  rule_ids: string[];
  hazard_ids: string[];
  required: boolean;
  effort: "S" | "M" | "L";
  cost_band: "free" | "$" | "$$" | "$$$";
  owner: "HOA" | "Owner" | "Unclear";
  priority: number;
}

export interface AgentStep {
  kind: "plan" | "tool_call" | "tool_result" | "verify" | "output" | "note";
  summary: string;
  detail?: Record<string, unknown> | null;
}

export interface ScoreBlock {
  score: number;
  label: string;
  fails: number;
  reviews: number;
  passes: number;
  zone0_met: number;
  zone0_total: number;
  unfilmed_sides: string[];
}

export interface VideoInfo {
  duration_s?: number;
  fps?: number;
  width?: number;
  height?: number;
  sam_fps?: number;
  [key: string]: unknown;
}

export interface Report {
  version: "1";
  scan_id: string;
  building_label: string;
  created_at: string;
  pack_id: string;
  pack_version: string;
  include_proposed: boolean;
  video: VideoInfo;
  eave_depth_ft?: Range | null;
  hazards: Hazard[];
  results: RuleResult[];
  score: ScoreBlock;
  fixes: Fix[];
  agent_trace: AgentStep[];
  cost: Record<string, unknown>;
  disclaimer: string;
}

/** Worker GET /scans/{id} response (docs/contracts/README.md). */
export type WorkerScanStatus = "queued" | "processing" | "done" | "failed";

export interface WorkerStage {
  name: string;
  status: string; // "pending" | "running" | "done" | "failed" | "skipped" (worker-defined)
  detail?: string | null;
}

export interface WorkerScan {
  scan_id: string;
  status: WorkerScanStatus;
  stage?: string | null;
  progress?: number | null;
  stages?: WorkerStage[];
  error?: string | null;
  report?: Report | null;
}

export const PIPELINE_STAGES = [
  "upload",
  "normalize",
  "frames",
  "segment",
  "measure",
  "rules",
  "narration",
  "agent",
  "report",
] as const;
export type PipelineStage = (typeof PIPELINE_STAGES)[number];

export const DEFAULT_DISCLAIMER =
  "EmberScan flags likely wildfire hazards and suggests fixes based on published defensible space rules. It is not an inspection and does not certify that any property is safe or compliant. Confirm requirements with your local fire authority.";
