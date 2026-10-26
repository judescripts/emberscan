"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";
import { loadSampleReport } from "@/app/actions";
import { buttonClass, cx, inputClass } from "../ui";

type Health = "checking" | "online" | "offline";

export function ScanForm({
  buildings,
  initialBuilding,
}: {
  buildings: { id: string; label: string; eave: string }[];
  initialBuilding: string | null;
}) {
  const router = useRouter();
  const [buildingId, setBuildingId] = useState(initialBuilding ?? buildings[0]?.id ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [health, setHealth] = useState<Health>("checking");
  const [uploadPct, setUploadPct] = useState<number | null>(null);
  const [error, setError] = useState<{ message: string; offline: boolean } | null>(null);
  const [samplePending, startSample] = useTransition();
  const xhrRef = useRef<XMLHttpRequest | null>(null);

  useEffect(() => {
    let alive = true;
    fetch("/api/worker/health", { cache: "no-store" })
      .then((r) => r.json())
      .then((j: { ok: boolean }) => alive && setHealth(j.ok ? "online" : "offline"))
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
    if (!file || !buildingId) return;
    setError(null);
    setUploadPct(0);
    const fd = new FormData();
    fd.append("video", file, file.name || "walkaround.mp4");
    const xhr = new XMLHttpRequest();
    xhrRef.current = xhr;
    xhr.open("POST", `/api/scans?building=${encodeURIComponent(buildingId)}`);
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
      const offline = body.error === "worker_unreachable";
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
        {health === "online" && <span>Scan pipeline online</span>}
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
          capture="environment"
          required
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className={cx(
            inputClass,
            "mt-1 file:mr-3 file:rounded-lg file:border-0 file:bg-soft file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-ink",
          )}
          aria-describedby="video-help"
        />
        <p id="video-help" className="mt-1 text-xs text-muted">
          Record now or pick a video. About 1–3 minutes, all four sides. {file && `Selected: ${file.name} (${(file.size / 1e6).toFixed(1)} MB)`}
        </p>
      </div>

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
          <p className="font-semibold text-fail">{error.offline ? "Couldn't reach the scan pipeline" : "Upload failed"}</p>
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
        <button type="submit" className={buttonClass("primary")} disabled={!file || !buildingId || uploading}>
          {uploading ? "Uploading…" : "Start scan"}
        </button>
        {health === "offline" && !error?.offline && sampleButton}
      </div>
    </form>
  );
}
