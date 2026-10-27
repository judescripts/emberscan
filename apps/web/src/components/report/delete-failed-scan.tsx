"use client";

import { deleteScan } from "@/app/actions";
import { ConfirmDelete } from "../manage/forms";

/** Remove a failed scan attempt from a building's history without leaving the page. */
export function DeleteFailedScan({ scanId }: { scanId: string }) {
  return <ConfirmDelete what="this failed attempt" consequence="Nothing else changes." onConfirm={() => deleteScan(scanId, true)} />;
}
