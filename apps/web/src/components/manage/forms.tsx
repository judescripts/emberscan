"use client";

import { useActionState, useState, useTransition } from "react";
import { deleteBuilding, deleteCommunity, saveBuilding, saveCommunity, type FormState } from "@/app/actions";
import { buttonClass, cx, inputClass } from "../ui";

const INITIAL: FormState = { ok: false };

function Message({ state }: { state: FormState }) {
  if (state.error)
    return (
      <p role="alert" className="text-sm font-semibold text-fail">
        {state.error}
      </p>
    );
  if (state.ok && state.message)
    return (
      <p role="status" className="text-sm font-semibold text-pass">
        {state.message}
      </p>
    );
  return null;
}

export interface CommunityValues {
  id?: string;
  name: string;
  type: "HOA" | "Condo" | "Home" | "Commercial";
  place: string;
  rulePack: string;
  includeProposed: boolean;
}

export function CommunityForm({
  values,
  packs,
}: {
  values: CommunityValues;
  packs: { id: string; label: string; available: boolean }[];
}) {
  const [state, action, pending] = useActionState(saveCommunity, INITIAL);
  const f = values.id ? `c-${values.id}` : "c-new";
  return (
    <form action={action} className="flex flex-col gap-4">
      {values.id && <input type="hidden" name="id" value={values.id} />}
      <div>
        <label htmlFor={`${f}-name`} className="text-sm font-semibold text-ink">
          Name
        </label>
        <input id={`${f}-name`} name="name" defaultValue={values.name} required maxLength={120} className={cx(inputClass, "mt-1")} placeholder="e.g. Oak Ridge HOA" />
      </div>
      <fieldset>
        <legend className="text-sm font-semibold text-ink">Type</legend>
        <div className="mt-1 flex flex-wrap gap-2">
          {(["HOA", "Condo", "Home", "Commercial"] as const).map((t) => (
            <label key={t} className="flex cursor-pointer items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2 text-sm has-[:checked]:border-brand has-[:checked]:bg-soft">
              <input type="radio" name="type" value={t} defaultChecked={values.type === t} className="accent-[var(--brand)]" />
              {t === "Home" ? "Single home" : t}
            </label>
          ))}
        </div>
      </fieldset>
      <div>
        <label htmlFor={`${f}-place`} className="text-sm font-semibold text-ink">
          Place
        </label>
        <input id={`${f}-place`} name="place" defaultValue={values.place} maxLength={120} className={cx(inputClass, "mt-1")} placeholder="City, county or fire district" />
      </div>
      <div>
        <label htmlFor={`${f}-pack`} className="text-sm font-semibold text-ink">
          Rule pack
        </label>
        <select id={`${f}-pack`} name="rule_pack" defaultValue={values.rulePack} className={cx(inputClass, "mt-1")}>
          {packs.map((p) => (
            <option key={p.id} value={p.id} disabled={!p.available}>
              {p.label}
              {p.available ? "" : " (coming soon)"}
            </option>
          ))}
        </select>
      </div>
      <label className="flex items-start gap-3 text-sm">
        <input type="checkbox" name="include_proposed" defaultChecked={values.includeProposed} className="mt-1 h-4 w-4 accent-[var(--brand)]" />
        <span>
          <span className="font-semibold text-ink">Include proposed rules</span>
          <span className="block text-xs text-muted">Shows California&apos;s proposed Zone 0 rules as “needs review”. They never change the score.</span>
        </span>
      </label>
      <Message state={state} />
      <div>
        <button type="submit" className={buttonClass("primary")} disabled={pending}>
          {pending ? "Saving…" : values.id ? "Save community" : "Create community"}
        </button>
      </div>
    </form>
  );
}

export interface BuildingValues {
  id?: string;
  communityId: string;
  label: string;
  units: string;
  eaveMode: "video" | "known" | "none";
  eaveFt: number | null;
  address: string;
}

export function BuildingForm({ values, onDone }: { values: BuildingValues; onDone?: () => void }) {
  const [state, action, pending] = useActionState(async (prev: FormState, fd: FormData) => {
    const res = await saveBuilding(prev, fd);
    if (res.ok) onDone?.();
    return res;
  }, INITIAL);
  const [mode, setMode] = useState(values.eaveMode);
  const f = values.id ? `b-${values.id}` : "b-new";
  return (
    <form action={action} className="flex flex-col gap-3">
      {values.id && <input type="hidden" name="id" value={values.id} />}
      <input type="hidden" name="community_id" value={values.communityId} />
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor={`${f}-label`} className="text-sm font-semibold text-ink">
            Label
          </label>
          <input id={`${f}-label`} name="label" defaultValue={values.label} required maxLength={120} className={cx(inputClass, "mt-1")} placeholder="Building C · Units 9–12" />
        </div>
        <div>
          <label htmlFor={`${f}-units`} className="text-sm font-semibold text-ink">
            Units
          </label>
          <input id={`${f}-units`} name="units" defaultValue={values.units} maxLength={120} className={cx(inputClass, "mt-1")} placeholder="9, 10, 11, 12" />
        </div>
      </div>
      <div>
        <label htmlFor={`${f}-address`} className="text-sm font-semibold text-ink">
          Street address <span className="font-normal text-muted">(optional)</span>
        </label>
        <input
          id={`${f}-address`}
          name="address"
          defaultValue={values.address}
          maxLength={200}
          autoComplete="street-address"
          className={cx(inputClass, "mt-1")}
          placeholder="28422 Constellation Rd, Valencia, CA 91355"
          aria-describedby={`${f}-address-help`}
        />
        <p id={`${f}-address-help`} className="mt-1 text-xs text-muted">
          EmberScan&apos;s research agent looks it up in public map data: fire hazard zone, which law applies, recent fires nearby.
        </p>
      </div>
      <fieldset>
        <legend className="text-sm font-semibold text-ink">Eave depth</legend>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2 text-sm has-[:checked]:border-brand has-[:checked]:bg-soft">
            <input type="radio" name="eave_mode" value="video" checked={mode === "video"} onChange={() => setMode("video")} className="accent-[var(--brand)]" />
            Measure from video
          </label>
          <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2 text-sm has-[:checked]:border-brand has-[:checked]:bg-soft">
            <input type="radio" name="eave_mode" value="known" checked={mode === "known"} onChange={() => setMode("known")} className="accent-[var(--brand)]" />
            I know it
          </label>
          <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2 text-sm has-[:checked]:border-brand has-[:checked]:bg-soft">
            <input type="radio" name="eave_mode" value="none" checked={mode === "none"} onChange={() => setMode("none")} className="accent-[var(--brand)]" />
            No overhang
          </label>
          {mode === "known" && (
            <span className="flex items-center gap-2">
              <label htmlFor={`${f}-eave`} className="sr-only">
                Eave depth in feet
              </label>
              <input
                id={`${f}-eave`}
                name="eave_ft"
                type="number"
                step="0.25"
                min="0.25"
                max="10"
                required
                defaultValue={values.eaveFt ?? ""}
                className={cx(inputClass, "w-24")}
              />
              <span className="text-sm text-muted">ft</span>
            </span>
          )}
        </div>
        <p className="mt-1 text-xs text-muted">
          Some proposed Zone 0 rules reach as far as the eaves stick out. Flat roof or parapet with nothing sticking out? Choose
          “No overhang” and skip the corner clips.
        </p>
      </fieldset>
      <Message state={state} />
      <div>
        <button type="submit" className={buttonClass(values.id ? "secondary" : "primary")} disabled={pending}>
          {pending ? "Saving…" : values.id ? "Save building" : "Add building"}
        </button>
      </div>
    </form>
  );
}

/** Inline two-step delete (no window.confirm). */
export function ConfirmDelete({
  what,
  consequence,
  onConfirm,
}: {
  what: string;
  consequence: string;
  onConfirm: () => Promise<void>;
}) {
  const [asking, setAsking] = useState(false);
  const [pending, start] = useTransition();
  if (!asking)
    return (
      <button type="button" className={buttonClass("ghost")} onClick={() => setAsking(true)}>
        Delete
      </button>
    );
  return (
    <div role="group" aria-label={`Confirm deleting ${what}`} className="flex flex-wrap items-center gap-2 rounded-xl border border-fail bg-fail-soft px-3 py-2 text-sm">
      <span className="text-ink">
        Delete {what}? {consequence}
      </span>
      <button type="button" className={buttonClass("danger")} disabled={pending} onClick={() => start(onConfirm)} autoFocus>
        {pending ? "Deleting…" : "Yes, delete"}
      </button>
      <button type="button" className={buttonClass("ghost")} onClick={() => setAsking(false)}>
        Cancel
      </button>
    </div>
  );
}

export function DeleteBuilding({ id, label }: { id: string; label: string }) {
  return <ConfirmDelete what={label} consequence="Its scans and fix tasks go too." onConfirm={() => deleteBuilding(id)} />;
}

export function DeleteCommunity({ id, name }: { id: string; name: string }) {
  return <ConfirmDelete what={name} consequence="All its buildings, scans and tasks go too." onConfirm={() => deleteCommunity(id)} />;
}

export function EditableBuilding({ values, summary }: { values: BuildingValues; summary: React.ReactNode }) {
  const [editing, setEditing] = useState(false);
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">{summary}</div>
        <div className="flex flex-wrap gap-1">
          <button type="button" className={buttonClass("ghost")} onClick={() => setEditing((e) => !e)} aria-expanded={editing}>
            {editing ? "Close" : "Edit"}
          </button>
          <DeleteBuilding id={values.id!} label={values.label} />
        </div>
      </div>
      {editing && <BuildingForm values={values} onDone={() => setEditing(false)} />}
    </div>
  );
}

/** "Add building" form that clears itself after each save. */
export function AddBuilding({ communityId }: { communityId: string }) {
  const [n, setN] = useState(0);
  return (
    <BuildingForm
      key={n}
      values={{ communityId, label: "", units: "", eaveMode: "video", eaveFt: null, address: "" }}
      onDone={() => setN((x) => x + 1)}
    />
  );
}
