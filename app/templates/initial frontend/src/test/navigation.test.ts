import { describe, expect, it } from "vitest";
import { routeForPortalLabel } from "../pages/StaffPortal";

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
});
