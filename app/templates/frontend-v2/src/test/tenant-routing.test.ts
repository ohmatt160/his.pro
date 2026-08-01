import { afterEach, describe, expect, it, vi } from "vitest";
import {
  getCanonicalPathForLegacyPath,
  getCanonicalSubdomainFromHostname,
  getCanonicalTenantUrl,
  getTenantBaseDomain,
  isValidCanonicalSubdomain,
} from "../lib/tenant-routing";

describe("tenant URL routing", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("extracts only one valid tenant label from the configured base domain", () => {
    expect(
      getCanonicalSubdomainFromHostname(
        "sunrise-medical.his-pro.vercel.app",
        "his-pro.vercel.app"
      )
    ).toBe("sunrise-medical");
    expect(
      getCanonicalSubdomainFromHostname(
        "nested.sunrise.his-pro.vercel.app",
        "his-pro.vercel.app"
      )
    ).toBe("");
    expect(
      getCanonicalSubdomainFromHostname(
        "sunrise.his-pro.vercel.app.evil.test",
        "his-pro.vercel.app"
      )
    ).toBe("");
  });

  it("rejects reserved and malformed subdomains", () => {
    expect(isValidCanonicalSubdomain("sunrise-medical")).toBe(true);
    expect(isValidCanonicalSubdomain("api")).toBe(false);
    expect(isValidCanonicalSubdomain("bad.host")).toBe(false);
    expect(isValidCanonicalSubdomain("a".repeat(64))).toBe(false);
  });

  it("builds a canonical URL from the deployment domain", () => {
    expect(
      getCanonicalTenantUrl(
        "sunrise-medical",
        "/dashboard/patients",
        "his-pro.vercel.app"
      )
    ).toBe("https://sunrise-medical.his-pro.vercel.app/dashboard/patients");
    expect(getCanonicalTenantUrl("sunrise-medical", "/login", "his.pro")).toBe(
      "https://sunrise-medical.his.pro/login"
    );
    expect(() =>
      getCanonicalTenantUrl("bad.host", "/login", "his.pro")
    ).toThrow();
    expect(() =>
      getCanonicalTenantUrl("sunrise-medical", "/login", "bad/domain")
    ).toThrow();
  });

  it("reads and validates the configured tenant base domain", () => {
    vi.stubEnv("VITE_TENANT_BASE_DOMAIN", "Hospitals.Example.Com.");
    expect(getTenantBaseDomain()).toBe("hospitals.example.com");

    vi.stubEnv("VITE_TENANT_BASE_DOMAIN", "hospitals.example.com/redirect");
    expect(() => getTenantBaseDomain()).toThrow(
      "The configured tenant base domain is invalid."
    );
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
