import { AERIAL_CREDIT, AERIAL_SIZE, aerialSrc, hasAerial } from "@/lib/aerial";
import type { BuildingNote } from "@/lib/report-types";
import { cx } from "./ui";

/**
 * Aerial photo around the building's address as its cover. No pin: the geocoded point is often on
 * the street, not the roof. Shows nothing until address research has found coordinates.
 * `bleed` pulls it to the edges of a Card.
 */
export function BuildingCover({
  building,
  bleed = false,
  className,
}: {
  building: { id: string; label: string; note: BuildingNote | null };
  bleed?: boolean;
  className?: string;
}) {
  if (!hasAerial(building.note)) return null;
  return (
    <figure
      className={cx(
        "relative m-0 overflow-hidden bg-soft",
        bleed ? "-mx-4 -mt-4 rounded-t-2xl sm:-mx-5 sm:-mt-5" : "rounded-2xl",
        className,
      )}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={aerialSrc(building.id)}
        alt={`Aerial photo around ${building.label}`}
        width={AERIAL_SIZE.width}
        height={AERIAL_SIZE.height}
        loading="lazy"
        className="block aspect-[2/1] h-auto w-full object-cover"
      />
      <figcaption className="absolute right-1.5 bottom-1.5 rounded bg-black/55 px-1.5 py-0.5 text-[10px] text-white">
        {AERIAL_CREDIT}
      </figcaption>
    </figure>
  );
}
