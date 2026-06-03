import { describe, expect, it } from "vitest";
import {
  formatTimelineDate,
  timelineModuleLabels,
  timelineModuleTone,
} from "../lib/patient-timeline";

describe("patient timeline helpers", () => {
  it("formats known and unknown timeline dates safely", () => {
    expect(formatTimelineDate("")).toBe("Unknown time");
    expect(formatTimelineDate("not-a-date")).toBe("not-a-date");
    expect(formatTimelineDate("2026-06-02T10:30:00")).toContain("2026");
  });

  it("labels and styles core timeline modules", () => {
    expect(timelineModuleLabels.lab).toBe("Laboratory");
    expect(timelineModuleLabels.billing).toBe("Billing");
    expect(timelineModuleTone.pharmacy).toContain("purple");
  });
});
