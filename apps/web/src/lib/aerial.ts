import type { BuildingNote } from "./report-types";

// Aerial cover photo for a building, from the coordinates address research found. USGS imagery
// is public domain: NAIP (about 60 cm per pixel) first, the National Map basemap as a fallback.
const NAIP = "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPPlus/ImageServer/exportImage";
const BASEMAP = "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/export";

export const AERIAL_SIZE = { width: 800, height: 400 };
const WIDTH_M = 260; // ground width of the picture: the building plus its 100 ft zones around it

export const AERIAL_CREDIT = "Aerial around the address · USGS";

export function hasAerial(note: BuildingNote | null | undefined): note is BuildingNote & { lat: number; lon: number } {
  return typeof note?.lat === "number" && typeof note?.lon === "number";
}

export function aerialSrc(buildingId: string) {
  return `/api/buildings/${buildingId}/aerial`;
}

/** Bounding box (lon/lat) centred on the point, with the picture's 2:1 shape. */
export function aerialBbox(lat: number, lon: number): [number, number, number, number] {
  const dLon = WIDTH_M / 2 / (111_320 * Math.cos((lat * Math.PI) / 180));
  const dLat = ((WIDTH_M / 2) * (AERIAL_SIZE.height / AERIAL_SIZE.width)) / 110_574;
  return [lon - dLon, lat - dLat, lon + dLon, lat + dLat];
}

function query(lat: number, lon: number) {
  const { width, height } = AERIAL_SIZE;
  return new URLSearchParams({
    bbox: aerialBbox(lat, lon).map((n) => n.toFixed(6)).join(","),
    bboxSR: "4326",
    imageSR: "3857",
    size: `${width},${height}`,
    format: "jpg",
    f: "image",
  });
}

/** The JPEG bytes, or null if neither USGS service answered with an image. */
export async function fetchAerial(lat: number, lon: number): Promise<ArrayBuffer | null> {
  for (const base of [NAIP, BASEMAP]) {
    try {
      const res = await fetch(`${base}?${query(lat, lon)}`, { signal: AbortSignal.timeout(12_000) });
      if (res.ok && res.headers.get("content-type")?.startsWith("image/")) return await res.arrayBuffer();
    } catch {
      // try the next service
    }
  }
  return null;
}
