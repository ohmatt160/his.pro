import { describe, expect, it } from "vitest";
import {
  canUsePortalRoute,
  resolvePortalTaskPath,
  routeForPortalLabel,
} from "../pages/StaffPortal";
import { roleAllows, routeRoles } from "../lib/role-access";

describe("navigation routing", () => {
  it("maps staff portal menu labels to real routed module pages", () => {
    const slug = "sunrise-medical-centre";

    expect(routeForPortalLabel("doctor", "Consultations", slug)).toBe(
      `/dashboard/${slug}/consultations`
    );
    expect(routeForPortalLabel("nurse", "Ward Board", slug)).toBe(
      `/dashboard/${slug}/wards`
    );
    expect(routeForPortalLabel("reception", "Check-ins", slug)).toBe(
      `/dashboard/${slug}/queue`
    );
    expect(routeForPortalLabel("pharmacist", "Inventory", slug)).toBe(
      `/dashboard/${slug}/inventory`
    );
    expect(routeForPortalLabel("lab", "Results", slug)).toBe(
      `/dashboard/${slug}/laboratory`
    );
  });

  it("maps doctor quick actions to routes doctors can open", () => {
    const slug = "sunrise-medical-centre";

    expect(routeForPortalLabel("doctor", "Patient Lookup", slug)).toBe(
      `/dashboard/${slug}/patients`
    );
    expect(routeForPortalLabel("doctor", "Write Prescription", slug)).toBe(
      `/dashboard/${slug}/pharmacy`
    );
    expect(routeForPortalLabel("doctor", "Order Lab Test", slug)).toBe(
      `/dashboard/${slug}/laboratory`
    );

    expect(roleAllows("doctor", routeRoles.patients)).toBe(true);
    expect(roleAllows("doctor", routeRoles.pharmacy)).toBe(true);
    expect(roleAllows("doctor", routeRoles.laboratory)).toBe(true);
  });

  it("does not expose the full patient registry to billing-only staff", () => {
    expect(roleAllows("billing", routeRoles.patients)).toBe(false);
    expect(roleAllows("billing", routeRoles.billing)).toBe(true);
    expect(
      canUsePortalRoute({
        key: "patients",
        modules: ["reception", "billing"],
        role: "billing",
      })
    ).toBe(false);
  });

  it("keeps staff portal actions aligned with role and module permissions", () => {
    const modules = ["reception", "records", "consultations", "lab", "pharmacy"];

    expect(canUsePortalRoute({ key: "patients", modules, role: "doctor" })).toBe(true);
    expect(canUsePortalRoute({ key: "pharmacy", modules, role: "doctor" })).toBe(true);
    expect(canUsePortalRoute({ key: "laboratory", modules, role: "doctor" })).toBe(true);
    expect(canUsePortalRoute({ key: "billing", modules, role: "doctor" })).toBe(false);
    expect(canUsePortalRoute({ key: "inventory", modules, role: "doctor" })).toBe(false);
  });

  it("resolves staff task links only inside the current workspace", () => {
    const slug = "sunrise-medical-centre";
    const modules = ["reception", "records", "consultations", "lab", "pharmacy"];

    expect(
      resolvePortalTaskPath({
        actionPath: "laboratory",
        facilitySlug: slug,
        modules,
        role: "doctor",
      })
    ).toBe(`/dashboard/${slug}/laboratory`);

    expect(
      resolvePortalTaskPath({
        actionPath: "https://example.com/phish",
        facilitySlug: slug,
        modules,
        role: "doctor",
      })
    ).toBeNull();
    expect(
      resolvePortalTaskPath({
        actionPath: "../admin",
        facilitySlug: slug,
        modules,
        role: "doctor",
      })
    ).toBeNull();
    expect(
      resolvePortalTaskPath({
        actionPath: "billing",
        facilitySlug: slug,
        modules,
        role: "doctor",
      })
    ).toBeNull();
  });
});
