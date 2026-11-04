import { afterEach, describe, expect, it, vi } from "vitest";
import { adminTokenOk, isLockedCommunity } from "./lock";

afterEach(() => vi.unstubAllEnvs());

describe("locked communities", () => {
  it("locks only the listed community ids", () => {
    vi.stubEnv("LOCKED_COMMUNITY_IDS", " aaa , bbb ");
    expect(isLockedCommunity("aaa")).toBe(true);
    expect(isLockedCommunity("bbb")).toBe(true);
    expect(isLockedCommunity("ccc")).toBe(false);
  });

  it("locks nothing when the list is empty", () => {
    vi.stubEnv("LOCKED_COMMUNITY_IDS", "");
    expect(isLockedCommunity("aaa")).toBe(false);
  });
});

describe("admin key", () => {
  it("accepts only the exact key", () => {
    vi.stubEnv("ADMIN_TOKEN", "s3cret-key");
    expect(adminTokenOk("s3cret-key")).toBe(true);
    expect(adminTokenOk("s3cret-key ")).toBe(false);
    expect(adminTokenOk("")).toBe(false);
    expect(adminTokenOk(undefined)).toBe(false);
  });

  it("refuses everyone when no key is configured", () => {
    vi.stubEnv("ADMIN_TOKEN", "");
    expect(adminTokenOk("")).toBe(false);
    expect(adminTokenOk("anything")).toBe(false);
  });
});
