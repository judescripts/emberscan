"use client";

import { useActionState, useTransition } from "react";
import { adminSignIn, adminSignOut, type FormState } from "@/app/actions";
import { buttonClass, inputClass } from "./ui";

const INITIAL: FormState = { ok: false };

export function AdminSignIn() {
  const [state, action, pending] = useActionState(adminSignIn, INITIAL);
  return (
    <form action={action} className="flex flex-col gap-3">
      <label className="flex flex-col gap-1 text-sm font-semibold text-ink">
        Admin key
        <input name="token" type="password" autoComplete="current-password" required className={inputClass} />
      </label>
      {state.error && (
        <p role="alert" className="text-sm font-semibold text-fail">
          {state.error}
        </p>
      )}
      <button type="submit" className={buttonClass("primary")} disabled={pending}>
        {pending ? "Checking…" : "Sign in"}
      </button>
    </form>
  );
}

export function AdminSignOut() {
  const [pending, start] = useTransition();
  return (
    <button type="button" className={buttonClass("secondary")} disabled={pending} onClick={() => start(() => adminSignOut())}>
      Sign out
    </button>
  );
}
