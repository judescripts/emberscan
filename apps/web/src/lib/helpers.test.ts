import { describe, expect, it } from "vitest";
import sample from "./sample-report.json";
import { describeDistance, formatNumber, formatRange, hazardMeasurements } from "./format";
import type { Report } from "./report-types";
import { computeScore, projectedScore, rulePenalty, scoreLabel, topFixes } from "./score";
import { rescanTransition } from "./tasks";
import { DEFAULT_GEOMETRY, layoutPins, zoneScale } from "./zonemap";

const report = sample as unknown as Report;

describe("score labels (ADR 0007)", () => {
  it("maps score bands to plain labels", () => {
    expect(scoreLabel(100)).toBe("In good shape");
    expect(scoreLabel(90)).toBe("In good shape");
    expect(scoreLabel(89)).toBe("A few fixes needed");
    expect(scoreLabel(75)).toBe("A few fixes needed");
    expect(scoreLabel(74)).toBe("Needs work");
    expect(scoreLabel(0)).toBe("Needs work");
  });

  it("counts adopted rules only, by zone weight", () => {
    expect(rulePenalty({ zone: "ALL", status: "fail", rule_status: "adopted" })).toBe(10);
    expect(rulePenalty({ zone: "Z1", status: "fail", rule_status: "adopted" })).toBe(8);
    expect(rulePenalty({ zone: "Z2", status: "fail", rule_status: "adopted" })).toBe(4);
    expect(rulePenalty({ zone: "Z1", status: "needs-review", rule_status: "adopted" })).toBe(4);
    expect(rulePenalty({ zone: "Z0", status: "fail", rule_status: "proposed" })).toBe(0);
  });

  it("reproduces the sample report's score and caps unfilmed sides at 80", () => {
    expect(computeScore(report.results)).toBe(report.score.score);
    expect(computeScore([], ["N"])).toBe(80);
  });

  it("projects the score after the top fixes", () => {
    const top = topFixes(report.fixes);
    expect(top[0].required).toBe(true);
    expect(projectedScore(report, top)).toBe(100);
  });
});

describe("plain-language distances", () => {
  it("formats numbers and ranges", () => {
    expect(formatNumber(6)).toBe("6");
    expect(formatNumber(0.3)).toBe("0.3");
    expect(formatNumber(12.4)).toBe("12");
    expect(formatRange({ min: 6, max: 9 })).toBe("6–9 ft");
    expect(formatRange({ min: 2, max: 2 })).toBe("2 ft");
    expect(formatRange({ min: 9, max: 6 })).toBe("6–9 ft");
  });

  it("says distance, reference, confidence and method in words", () => {
    expect(describeDistance({ min: 6, max: 9 }, "chimney", "medium", "marker")).toBe(
      "About 6–9 ft from the chimney · fairly sure, measured with the marker",
    );
    expect(describeDistance({ min: 0, max: 0.5 }, null, "low", "visual")).toBe(
      "About 0–0.5 ft from the wall · not sure, estimated by eye from the video",
    );
  });

  it("lists clearance before wall distance", () => {
    const juniper = report.hazards.find((h) => h.id === "h-shrub-0")!;
    const lines = hazardMeasurements(juniper);
    expect(lines[0]).toContain("from the window");
    expect(lines[1]).toContain("from the wall");
  });
});

describe("zone-map scale", () => {
  it("is piecewise linear and monotonic with Zone 0 stretched", () => {
    expect(zoneScale(0)).toBe(0);
    expect(zoneScale(-3)).toBe(0);
    expect(zoneScale(5)).toBeCloseTo(0.26);
    expect(zoneScale(30)).toBeCloseTo(0.66);
    expect(zoneScale(100)).toBe(1);
    expect(zoneScale(500)).toBe(1);
    expect(zoneScale(2.5)).toBeCloseTo(0.13);
    // Zone 0 gets far more than its 5% share of the radius
    expect(zoneScale(5)).toBeGreaterThan(0.2);
    for (let ft = 0; ft < 100; ft += 0.5) expect(zoneScale(ft + 0.5)).toBeGreaterThanOrEqual(zoneScale(ft));
  });

  it("places one pin per mapped hazard, outside the building on its side", () => {
    const pins = layoutPins(report.hazards, DEFAULT_GEOMETRY);
    expect(pins).toHaveLength(report.hazards.length);
    const south = pins.filter((p) => report.hazards.find((h) => h.id === p.hazardId)!.side === "S");
    const b = (DEFAULT_GEOMETRY.size + DEFAULT_GEOMETRY.buildingH) / 2;
    south.forEach((p) => expect(p.y).toBeGreaterThan(b));
  });
});

describe("fix tracking on rescan", () => {
  it("verifies only through a rescan that clears the rule", () => {
    expect(rescanTransition("fixed", "pass", true).status).toBe("verified");
    expect(rescanTransition("fixed", "fail", true).status).toBe("open");
    expect(rescanTransition("wontfix", "pass", false).status).toBe("wontfix");
    expect(rescanTransition("open", "needs-review", true).status).toBe("open");
  });
});
