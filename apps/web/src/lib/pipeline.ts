import { PIPELINE_STAGES, type PipelineStage, type WorkerStage } from "./report-types";

/** What each worker stage does, in plain words, and which model or tool does it. */
export const STAGE_INFO: Record<PipelineStage, { title: string; what: string; tool: string }> = {
  upload: { title: "Upload", what: "Your clips go to the EmberScan pipeline. Film the property, not people: anyone caught by accident is blurred next.", tool: "Web app → worker" },
  normalize: { title: "Prepare video", what: "Fixes rotation and frame rate so every frame lines up.", tool: "ffmpeg" },
  frames: { title: "Pick frames", what: "Samples the walkaround and keeps the sharpest frames.", tool: "Keyframe selector" },
  segment: { title: "Find and track hazards", what: "Finds mulch, shrubs, firewood, fences… and follows each one across the video.", tool: "SAM 3.1" },
  privacy: {
    title: "Privacy guard",
    what: "SAM 3.1 looks for people and license plates in every frame and blurs each one, with a margin, before anything is measured or kept. If the check can't run, the scan stops rather than keep unblurred frames. Always on.",
    tool: "SAM 3.1 + blur",
  },
  measure: { title: "Measure distances", what: "Uses the scale marker and the ground to turn pixels into feet, as ranges.", tool: "Marker + ground plane" },
  eaves: { title: "Read the eaves", what: "Estimates how far the roof overhangs from your corner clips, as a range.", tool: "Muse Spark (vision)" },
  rules: { title: "Check the rules", what: "Checks every rule in the pack, with citations. Same input, same result.", tool: "Rules engine (us-ca)" },
  narration: { title: "Listen to narration", what: "Ties what you said while filming to the hazards near that moment.", tool: "Muse Voice Transcribe" },
  agent: {
    title: "Plan the fixes",
    what: "Plans, calls tools over the results and verifies every claim. Then Muse Image pictures the top fixes from blurred frames, and Muse Spark drops any picture that doesn't show its fix.",
    tool: "Muse Spark Open agent + Muse Image",
  },
  report: { title: "Write the report", what: "Score, evidence, fix plan and citations in one report. The raw video and audio are deleted; only blurred frames are kept.", tool: "Report builder" },
};

export type StageState = "pending" | "running" | "done" | "failed" | "skipped";

export function normalizeStageStatus(s: string | null | undefined): StageState {
  const v = (s ?? "").toLowerCase();
  if (["done", "complete", "completed", "ok", "success"].includes(v)) return "done";
  if (["running", "processing", "active", "in_progress"].includes(v)) return "running";
  if (["failed", "error"].includes(v)) return "failed";
  if (["skipped", "skip"].includes(v)) return "skipped";
  return "pending";
}

export interface StageRow {
  name: string;
  title: string;
  what: string;
  tool: string;
  state: StageState;
  detail: string | null;
}

/**
 * Merge the worker's stage list with the known order. If the worker sends no stage list,
 * infer states from the current stage name and overall status.
 */
export function stageRows(
  stages: WorkerStage[] | null | undefined,
  current: string | null | undefined,
  status: string,
): StageRow[] {
  const byName = new Map((stages ?? []).map((s) => [s.name, s]));
  const currentIdx = current ? PIPELINE_STAGES.indexOf(current as PipelineStage) : -1;
  const rows: StageRow[] = PIPELINE_STAGES.map((name, i) => {
    const info = STAGE_INFO[name];
    const w = byName.get(name);
    let state: StageState;
    if (w) state = normalizeStageStatus(w.status);
    else if (status === "done") state = "done";
    else if (currentIdx >= 0) state = i < currentIdx ? "done" : i === currentIdx ? (status === "failed" ? "failed" : "running") : "pending";
    else state = "pending";
    return { name, ...info, state, detail: w?.detail ?? null };
  });
  // Stages the worker reports that we don't know yet still show up, at the end.
  for (const s of stages ?? []) {
    if (!(PIPELINE_STAGES as readonly string[]).includes(s.name)) {
      rows.push({ name: s.name, title: s.name, what: "", tool: "", state: normalizeStageStatus(s.status), detail: s.detail ?? null });
    }
  }
  return rows;
}
