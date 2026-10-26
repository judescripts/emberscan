const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Route params are user input; check the shape before handing them to a uuid column. */
export function isUuid(s: string | null | undefined): s is string {
  return typeof s === "string" && UUID.test(s);
}
