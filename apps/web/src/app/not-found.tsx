import { ButtonLink } from "@/components/ui";

export default function NotFound() {
  return (
    <main className="py-10">
      <h1 className="text-2xl font-bold text-ink">Not found</h1>
      <p className="mt-1 text-muted">That building, scan or community doesn&apos;t exist (or was deleted).</p>
      <ButtonLink href="/" className="mt-4">
        Back to buildings
      </ButtonLink>
    </main>
  );
}
