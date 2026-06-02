import { describe, expect, it } from "vitest";
import { defaultReportRange, formatMoney, statusSummary } from "../lib/reports";

describe("report helpers", () => {
  it("builds a stable default 30-day report range", () => {
    expect(defaultReportRange(new Date("2026-06-02T12:00:00Z"))).toEqual({
      date_from: "2026-05-03",
      date_to: "2026-06-02",
    });
  });

  it("formats status summaries for report cards", () => {
    expect(
      statusSummary({
        total: 3,
        by_status: { in_progress: 1, waiting: 2 },
      })
    ).toBe("in progress: 1 · waiting: 2");
  });

  it("formats naira values for revenue reports", () => {
    expect(formatMoney(25000)).toContain("25,000");
  });
});
