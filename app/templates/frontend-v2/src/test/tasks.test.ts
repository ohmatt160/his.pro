import { describe, expect, it } from "vitest";
import { formatTaskTime, taskTone, type WorkTask } from "../lib/tasks";

const task = (overrides: Partial<WorkTask>): WorkTask => ({
  id: "task-1",
  title: "Collect sample",
  description: "Full Blood Count",
  role: "LAB_TECH",
  module: "lab",
  priority: "normal",
  status: "open",
  source_type: "lab_order",
  source_id: "order-1",
  action_path: "laboratory",
  created_at: "2026-06-02T10:30:00",
  metadata: {},
  ...overrides,
});

describe("work task helpers", () => {
  it("maps task priority to queue tone", () => {
    expect(taskTone("urgent")).toBe("critical");
    expect(taskTone("high")).toBe("critical");
    expect(taskTone("normal")).toBe("warning");
    expect(taskTone("low")).toBe("success");
  });

  it("formats due time before created time", () => {
    expect(formatTaskTime(task({ due_at: "2026-06-02T12:45:00" }))).toContain("12");
    expect(formatTaskTime(task({ created_at: "" }))).toBe("Now");
  });
});
