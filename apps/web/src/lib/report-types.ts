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
  /** How much of the rule's area the video covered; "none" = beyond it, not in the score. */
  coverage?: "full" | "partial" | "none";
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
  /** Muse Image "after" picture of the fix: an illustration, never evidence. */
  illustration?: Illustration | null;
}

export interface Illustration {
  before_path: string;
  after_path: string;
  hazard_id: string;
  frame_index: number;
  model: string;
  prompt: string;
  checked?: boolean; // Muse Spark compared the pair and saw the fix
  check_reason?: string;
}

export interface AgentStep {
  kind: "privacy" | "plan" | "tool_call" | "tool_result" | "verify" | "output" | "illustrate" | "note";
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
  not_covered?: number;
  covered_ft?: number | null;
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
  eave_source?: "entered" | "corner_video" | null;
  eave_estimate?: { confidence: string; reason: string; frames: string[]; model: string } | null;
  hazards: Hazard[];
  results: RuleResult[];
  score: ScoreBlock;
  fixes: Fix[];
  agent_trace: AgentStep[];
  /** The model that planned the fixes; null/absent = rule-based fallback (or an older report). */
  agent_model?: AgentModel | null;
  /** What the privacy guard blurred and deleted; absent on reports from before Oct 27. */
  privacy?: PrivacyInfo | null;
  cost: Record<string, unknown>;
  disclaimer: string;
}

export interface PrivacyInfo {
  people: number;
  plates: number;
  frames_blurred: number;
  regions_blurred: number;
  raw_deleted: string[];
  checked: boolean;
  summary: string;
  model: string;
}

export interface AgentModel {
  model: string;
  provider: "baseten" | "meta";
  label: string;
  seconds?: number;
}

/** Worker GET /scans/{id} response (docs/contracts/README.md). */
export type WorkerScanStatus = "queued" | "processing" | "done" | "failed";

/** Address research note from the worker's POST /research (workers/.../research.py). */
export interface BuildingNote {
  address: string;
  matched_address: string | null;
  lat: number | null;
  lon: number | null;
  county: string | null;
  city: string | null;
  hazard_class: string | null;
  responsibility: string | null;
  summary: string;
  facts: { label: string; value: string; source_id: string }[];
  to_check: string[];
  sources: { id: string; name: string; url: string }[];
  trace: AgentStep[];
  model: string | null;
  cost_usd: number;
  generated_at: string;
  disclaimer: string;
}

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
  "narration", // runs alongside tracking, so it's listed next to it
  "segment",
  "privacy",
  "measure",
  "rules",
  "agent",
  "report",
] as const;
export type PipelineStage = (typeof PIPELINE_STAGES)[number];

export const DEFAULT_DISCLAIMER =
  "EmberScan flags likely wildfire hazards and suggests fixes based on published defensible space rules. It is not an inspection and does not certify that any property is safe or compliant. Confirm requirements with your local fire authority.";
