import type { Metadata } from "next";
import { Suspense } from "react";
import { AdminSignIn, AdminSignOut } from "@/components/admin-forms";
import { Card, PageHeader, Skeleton } from "@/components/ui";
import { isAdmin } from "@/lib/lock";

export const metadata: Metadata = { title: "Admin", robots: { index: false } };

export default function AdminPage() {
  return (
    <main>
      <PageHeader title="Admin" kicker="Locked example communities" />
      <Card className="max-w-md">
        <Suspense fallback={<Skeleton lines={2} />}>
          <Status />
        </Suspense>
      </Card>
    </main>
  );
}

async function Status() {
  if (await isAdmin()) {
    return (
      <div className="flex flex-col gap-3 text-sm">
        <p className="text-ink">You&apos;re signed in as admin on this browser. Locked communities can be edited here.</p>
        <AdminSignOut />
      </div>
    );
  }
  return <AdminSignIn />;
}
