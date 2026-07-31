import { describe, expect, it } from "vitest";
import {
  getCanonicalPathForLegacyPath,
  getCanonicalSubdomainFromHostname,
  getCanonicalTenantUrl,
  isValidCanonicalSubdomain,
} from "../lib/tenant-routing";

describe("tenant URL routing", () => {
  it("extracts only one valid tenant label from the configured base domain", () => {
    expect(
      getCanonicalSubdomainFromHostname(
        "sunrise-medical.app.his.pro",
        "app.his.pro"
      )
    ).toBe("sunrise-medical");
    expect(
      getCanonicalSubdomainFromHostname("nested.sunrise.app.his.pro", "app.his.pro")
    ).toBe("");
    expect(
      getCanonicalSubdomainFromHostname("sunrise.app.his.pro.evil.test", "app.his.pro")
    ).toBe("");
  });

  it("rejects reserved and malformed subdomains", () => {
    expect(isValidCanonicalSubdomain("sunrise-medical")).toBe(true);
    expect(isValidCanonicalSubdomain("api")).toBe(false);
    expect(isValidCanonicalSubdomain("bad.host")).toBe(false);
    expect(isValidCanonicalSubdomain("a".repeat(64))).toBe(false);
  });

  it("builds a fixed-domain canonical URL", () => {
    expect(getCanonicalTenantUrl("sunrise-medical", "/dashboard/patients")).toBe(
      "https://sunrise-medical.app.his.pro/dashboard/patients"
    );
    expect(() => getCanonicalTenantUrl("bad.host", "/login")).toThrow();
  });

  it.each([
    ["/sunrise-medical", "/login"],
    ["/sunrise-medical/login", "/login"],
    ["/login/sunrise-medical", "/login"],
    ["/dashboard/sunrise-medical", "/dashboard"],
    ["/dashboard/sunrise-medical/patients", "/dashboard/patients"],
    ["/portal/sunrise-medical", "/portal"],
    [
      "/sunrise-medical/branches/lagos/dashboard/patients",
      "/branches/lagos/dashboard/patients",
    ],
    ["/hospital/sunrise-medical", "/hospital"],
  ])("normalizes legacy path %s", (legacyPath, canonicalPath) => {
    expect(getCanonicalPathForLegacyPath(legacyPath, "sunrise-medical")).toBe(
      canonicalPath
    );
  });

  it("does not rewrite another tenant or a canonical module path", () => {
    expect(
      getCanonicalPathForLegacyPath("/dashboard/another-hospital", "sunrise-medical")
    ).toBe("/dashboard/another-hospital");
    expect(
      getCanonicalPathForLegacyPath("/dashboard/patients", "sunrise-medical")
    ).toBe("/dashboard/patients");
  });
});
