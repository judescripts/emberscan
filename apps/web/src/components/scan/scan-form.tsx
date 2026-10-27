"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";
import { loadSampleReport } from "@/app/actions";
import { buttonClass, cx, inputClass } from "../ui";

type Health = "checking" | "online" | "offline";

function sortByName(list: FileList | null): File[] {
  return [...(list ?? [])].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
}

function clipSummary(files: File[]): string {
  if (!files.length) return "";
  const mb = files.reduce((s, f) => s + f.size, 0) / 1e6;
  return files.length === 1
    ? `Selected: ${files[0].name} (${mb.toFixed(1)} MB)`
    : `Selected ${files.length} clips (${mb.toFixed(1)} MB): ${files.map((f) => f.name).join(", ")}`;
}

export function ScanForm({
  buildings,
  initialBuilding,
}: {
  buildings: { id: string; label: string; eave: string }[];
  initialBuilding: string | null;
}) {
  const router = useRouter();
  const [buildingId, setBuildingId] = useState(initialBuilding ?? buildings[0]?.id ?? "");
  const [files, setFiles] = useState<File[]>([]);
  const [corners, setCorners] = useState<File[]>([]);
  const [sides, setSides] = useState<string[]>([]);
  const [health, setHealth] = useState<Health>("checking");
  const [uploadPct, setUploadPct] = useState<number | null>(null);
  const [error, setError] = useState<{ message: string; offline: boolean } | null>(null);
  const [needsPasscode, setNeedsPasscode] = useState(false);
  const [passcode, setPasscode] = useState("");
  const [scansLeft, setScansLeft] = useState<number | null>(null);
  const [samplePending, startSample] = useTransition();
  const xhrRef = useRef<XMLHttpRequest | null>(null);

  useEffect(() => {
    let alive = true;
    fetch("/api/worker/health", { cache: "no-store" })
      .then((r) => r.json())
      .then((j: { ok: boolean; passcodeRequired?: boolean; scansLeftToday?: number | null }) => {
        if (!alive) return;
        setHealth(j.ok ? "online" : "offline");
        setNeedsPasscode(Boolean(j.passcodeRequired));
        setScansLeft(j.scansLeftToday ?? null);
      })
      .catch(() => alive && setHealth("offline"));
    return () => {
      alive = false;
      xhrRef.current?.abort();
    };
  }, []);

  const building = buildings.find((b) => b.id === buildingId);
  const uploading = uploadPct !== null;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!files.length || !buildingId) return;
    setError(null);
    setUploadPct(0);
    const fd = new FormData();
    for (const f of files) fd.append("video", f, f.name || "walkaround.mp4");
    for (const f of corners) fd.append("corner", f, f.name || "corner.mp4");
    if (sides.some(Boolean)) fd.append("clip_sides", files.map((_, i) => sides[i] ?? "").join(","));
    const xhr = new XMLHttpRequest();
    xhrRef.current = xhr;
    xhr.open("POST", `/api/scans?building=${encodeURIComponent(buildingId)}`);
    if (needsPasscode) xhr.setRequestHeader("x-scan-passcode", passcode);
    xhr.upload.onprogress = (ev) => {
      if (ev.lengthComputable) setUploadPct(Math.round((ev.loaded / ev.total) * 100));
    };
    xhr.onload = () => {
      let body: { scanId?: string; error?: string; message?: string } = {};
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        /* non-JSON error page */
      }
      if (xhr.status === 201 && body.scanId) {
        router.push(`/scan/${body.scanId}`);
        return;
      }
      setUploadPct(null);
      // Over budget behaves like offline: the sample report is the way to see a result.
      const offline = body.error === "worker_unreachable" || body.error === "budget";
      if (offline) setHealth("offline");
      setError({ message: body.message ?? `Upload failed (${xhr.status}).`, offline });
    };
    xhr.onerror = () => {
      setUploadPct(null);
      setError({ message: "The upload was interrupted. Check your connection and try again.", offline: false });
    };
    xhr.send(fd);
  }

  const sampleButton = (
    <button
      type="button"
      className={buttonClass("secondary")}
      disabled={!buildingId || samplePending}
      onClick={() => startSample(() => loadSampleReport(buildingId))}
    >
      {samplePending ? "Loading sample…" : "Load sample report"}
    </button>
  );

  return (
    <form onSubmit={submit} className="flex flex-col gap-4" aria-describedby="worker-status">
      <div className="flex flex-wrap items-center gap-2 text-sm" id="worker-status" role="status">
        <span
          className={cx(
            "h-2.5 w-2.5 rounded-full",
            health === "online" ? "bg-pass" : health === "offline" ? "bg-fail" : "es-pulse bg-muted",
          )}
          aria-hidden
        />
        {health === "online" && (
          <span>
            Scan pipeline online
            {scansLeft !== null && (
              <span className="text-muted">
                {" "}
                · {scansLeft === 0 ? "daily scan budget used up" : `${scansLeft} scan${scansLeft === 1 ? "" : "s"} left today`}
              </span>
            )}
          </span>
        )}
        {health === "checking" && <span className="text-muted">Checking the scan pipeline…</span>}
        {health === "offline" && <span>Scan pipeline offline. You can still load the sample report to see the result.</span>}
      </div>

      <div>
        <label htmlFor="building" className="text-sm font-semibold text-ink">
          Building
        </label>
        <select id="building" value={buildingId} onChange={(e) => setBuildingId(e.target.value)} className={cx(inputClass, "mt-1")} required>
          {buildings.map((b) => (
            <option key={b.id} value={b.id}>
              {b.label}
            </option>
          ))}
        </select>
        {building && <p className="mt-1 text-xs text-muted">{building.eave}</p>}
      </div>

      <div>
        <label htmlFor="video" className="text-sm font-semibold text-ink">
          Walkaround video
        </label>
        <input
          id="video"
          name="video"
          type="file"
          accept="video/*"
          multiple
          required
          onChange={(e) => {
            setFiles(sortByName(e.target.files));
            setSides([]);
          }}
          className={cx(
            inputClass,
            "mt-1 file:mr-3 file:rounded-lg file:border-0 file:bg-soft file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-ink",
          )}
          aria-describedby="video-help"
        />
        <p id="video-help" className="mt-1 text-xs text-muted">
          One loop of all four sides, about 1–3 minutes. Several clips are fine: they&apos;re joined in name order. {clipSummary(files)}
        </p>
        {files.length === 0 && (
          <div className="mt-3 rounded-xl border border-dashed border-line px-3 py-2.5 text-xs text-muted">
            <p className="font-semibold text-ink">Which side is each clip? (N / E / S / W)</p>
            <p className="mt-0.5">
              Once you pick your clips, each one shows up here with N, E, S and W buttons. Tagging sides puts hazards on the zone
              map. Or just say “north side…” while filming.
            </p>
          </div>
        )}
        {files.length > 0 && (
          <fieldset className="mt-3">
            <legend className="text-sm font-semibold text-ink">
              Which side is each clip? <span className="font-normal text-muted">(optional, puts hazards on the zone map)</span>
            </legend>
            <ul className="mt-1 flex flex-col gap-1.5">
              {files.map((f, i) => (
                <li key={f.name + i} className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="min-w-0 flex-1 truncate text-muted" title={f.name}>
                    {i + 1}. {f.name}
                  </span>
                  <span className="flex gap-1" role="radiogroup" aria-label={`Side for ${f.name}`}>
                    {(["N", "E", "S", "W"] as const).map((s) => {
                      const on = sides[i] === s;
                      return (
                        <button
                          key={s}
                          type="button"
                          role="radio"
                          aria-checked={on}
                          aria-label={{ N: "North", E: "East", S: "South", W: "West" }[s]}
                          onClick={() =>
                            setSides((prev) => {
                              const next = files.map((_, j) => prev[j] ?? "");
                              next[i] = on ? "" : s;
                              return next;
                            })
                          }
                          className={cx(
                            "h-8 w-8 rounded-lg border text-xs font-bold",
                            on ? "border-brand bg-brand text-brand-fg" : "border-line bg-surface text-ink",
                          )}
                        >
                          {s}
                        </button>
                      );
                    })}
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-1 text-xs text-muted">Or just say “north side…” while you film.</p>
          </fieldset>
        )}
      </div>

      <div>
        <label htmlFor="corner" className="text-sm font-semibold text-ink">
          Corner clips <span className="font-normal text-muted">(optional, for eave depth)</span>
        </label>
        <input
          id="corner"
          name="corner"
          type="file"
          accept="video/*"
          multiple
          onChange={(e) => setCorners(sortByName(e.target.files))}
          className={cx(
            inputClass,
            "mt-1 file:mr-3 file:rounded-lg file:border-0 file:bg-soft file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-ink",
          )}
          aria-describedby="corner-help"
        />
        <p id="corner-help" className="mt-1 text-xs text-muted">
          3–5 s at each corner, filmed along the wall so the roof overhang shows in profile, marker on the ground. All four
          corners if the eaves differ. {clipSummary(corners)}
        </p>
      </div>

      {needsPasscode && (
        <div>
          <label htmlFor="passcode" className="text-sm font-semibold text-ink">
            Scan passcode
          </label>
          <input
            id="passcode"
            type="password"
            autoComplete="off"
            value={passcode}
            onChange={(e) => setPasscode(e.target.value)}
            required
            className={cx(inputClass, "mt-1")}
            aria-describedby="passcode-help"
          />
          <p id="passcode-help" className="mt-1 text-xs text-muted">
            Live scans call paid AI models, so they need a passcode. Anyone can browse the sample report.
          </p>
        </div>
      )}

      {uploading && (
        <div>
          <div className="flex justify-between text-sm">
            <span>Uploading to the pipeline…</span>
            <span className="tabular-nums">{uploadPct}%</span>
          </div>
          <div className="mt-1 h-2.5 overflow-hidden rounded-full bg-soft" role="progressbar" aria-valuenow={uploadPct ?? 0} aria-valuemin={0} aria-valuemax={100} aria-label="Upload progress">
            <div className="es-stripes h-full rounded-full bg-brand transition-[width]" style={{ width: `${uploadPct}%` }} />
          </div>
        </div>
      )}

      {error && (
        <div role="alert" className="rounded-xl border border-fail bg-fail-soft p-3 text-sm text-ink">
          <p className="font-semibold text-fail">{error.offline ? "Can't run a scan right now" : "Upload failed"}</p>
          <p className="mt-0.5">{error.message}</p>
          {error.offline && (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {sampleButton}
              <span className="text-xs text-muted">Attaches the sample report to this building, marked “Sample”.</span>
            </div>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <button type="submit" className={buttonClass("primary")} disabled={!files.length || !buildingId || uploading || (needsPasscode && !passcode)}>
          {uploading ? "Uploading…" : "Start scan"}
        </button>
        {health === "offline" && !error?.offline && sampleButton}
      </div>
    </form>
  );
}
