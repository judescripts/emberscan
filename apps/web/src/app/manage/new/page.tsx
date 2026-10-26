import type { Metadata } from "next";
import { CommunityForm } from "@/components/manage/forms";
import { Card, PageHeader } from "@/components/ui";
import { PACK_OPTIONS } from "@/lib/rules";

export const metadata: Metadata = { title: "New community" };

export default function NewCommunityPage() {
  return (
    <main>
      <PageHeader title="New community" kicker="An HOA, a condo complex, or a single home" />
      <Card className="max-w-xl">
        <CommunityForm
          packs={PACK_OPTIONS.map((p) => ({ ...p }))}
          values={{ name: "", type: "HOA", place: "", rulePack: "us-ca", includeProposed: true }}
        />
      </Card>
      <p className="mt-4 text-xs text-muted">
        After creating it, add buildings. Each building gets its own walkaround scan, measured against the community&apos;s rule pack.
      </p>
    </main>
  );
}
