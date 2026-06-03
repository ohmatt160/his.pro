import { describe, expect, it } from "vitest";
import {
  canAccessModule,
  getDefaultModules,
  getRouteModuleId,
  getModulePath,
  isModuleEnabled,
  isRoleAllowedForModule,
  normalizeModules,
} from "../lib/modules";

describe("facility modules", () => {
  it("normalizes supported module aliases and removes duplicates", () => {
    expect(
      normalizeModules([
        "patients",
        "reception",
        "medical_records",
        "records",
        "dashboard",
        "unknown",
      ])
    ).toEqual(["reception", "records", "reports"]);
  });

  it("returns scalable defaults by facility type", () => {
    expect(getDefaultModules("clinic")).toEqual([
      "reception",
      "records",
      "consultations",
      "pharmacy",
      "billing",
    ]);
    expect(getDefaultModules("hospital")).toContain("radiology");
    expect(getDefaultModules("pharmacy")).toEqual([
      "pharmacy",
      "inventory",
      "billing",
      "reports",
    ]);
  });

  it("maps enabled modules to dashboard paths", () => {
    const modules = ["reception", "lab"];

    expect(isModuleEnabled(modules, "reception")).toBe(true);
    expect(isModuleEnabled(modules, "billing")).toBe(false);
    expect(getModulePath("sunrise", "lab")).toBe("/dashboard/sunrise/laboratory");
  });

  it("enforces role access on enabled modules", () => {
    const modules = ["reception", "records", "lab", "pharmacy"];

    expect(isRoleAllowedForModule("doctor", "lab")).toBe(true);
    expect(isRoleAllowedForModule("nurse", "lab")).toBe(false);
    expect(canAccessModule({ modules, moduleId: "lab", role: "doctor" })).toBe(true);
    expect(canAccessModule({ modules, moduleId: "lab", role: "nurse" })).toBe(false);
    expect(canAccessModule({ modules, moduleId: "billing", role: "reception" })).toBe(false);
  });

  it("maps staff labels to module ids for portal filtering", () => {
    expect(getRouteModuleId("Shared Patient Record")).toBe("records");
    expect(getRouteModuleId("Patient Lookup")).toBe("reception");
    expect(getRouteModuleId("Medication Round")).toBe("pharmacy");
    expect(getRouteModuleId("Lab Orders")).toBe("lab");
  });
});
