import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  getFacilityWorkspace,
  getFacilityPlatformLink,
  saveFacilityWorkspace,
  updateCachedFacilityWorkspace,
  WORKSPACE_UPDATED_EVENT,
} from "../lib/facility-workspace";
import { getFacilityLoginPath } from "../lib/facility-staff";

const fetchMock = () => fetch as unknown as ReturnType<typeof vi.fn>;

describe("facility workspace API", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("atomically onboards a facility owner and caches the workspace", async () => {
    fetchMock().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          access_token: "access-token",
          refresh_token: "refresh-token",
          token_type: "bearer",
          facility: {
            id: "facility-1",
            name: "Sunrise Medical Centre",
            slug: "sunrise-medical-centre",
            type: "hospital",
            country: "Nigeria",
            phone: "+234 800 000 0000",
            email: "admin@sunrise.test",
            modules: ["reception", "records"],
            created_at: "2026-05-31T10:00:00",
          },
        }),
        { status: 200 }
      )
    );

    const workspace = await saveFacilityWorkspace({
      facilityName: "Sunrise Medical Centre",
      facilityType: "hospital",
      country: "Nigeria",
      fullName: "Dr. Amina Yusuf",
      email: "admin@sunrise.test",
      phone: "+234 800 000 0000",
      adminPassword: "Password1",
      selectedModules: ["reception", "records"],
    });

    expect(fetchMock()).toHaveBeenCalledTimes(1);
    expect(fetchMock().mock.calls[0][0]).toBe("/api/v1/auth/onboard");
    expect(fetchMock().mock.calls[0][1].body).toBe(
      JSON.stringify({
        owner: {
          username: "sunrise-medical-centre-admin",
          email: "admin@sunrise.test",
          password: "Password1",
          first_name: "Dr.",
          last_name: "Amina Yusuf",
        },
        facility: {
          name: "Sunrise Medical Centre",
          type: "hospital",
          country: "Nigeria",
          phone: "+234 800 000 0000",
          email: "admin@sunrise.test",
          modules: ["reception", "records"],
          settings: {
            administrator: {
              fullName: "Dr. Amina Yusuf",
              username: "sunrise-medical-centre-admin",
            },
          },
        },
      })
    );
    expect(workspace.facilitySlug).toBe("sunrise-medical-centre");
    expect(workspace.canonicalSubdomain).toBe("sunrise-medical-centre");
    expect(window.localStorage.getItem("hispro.auth.token")).toBeNull();
    expect(window.localStorage.getItem("hispro.auth.user")).toBeNull();
  });

  it("generates the workspace URL as a login entry point", () => {
    expect(getFacilityLoginPath("sunrise-medical-centre")).toBe(
      "/sunrise-medical-centre"
    );
    expect(getFacilityPlatformLink("sunrise-medical-centre")).toBe(
      "http://localhost:3000/sunrise-medical-centre"
    );
  });

  it("loads a cold workspace from the public facility workspace endpoint", async () => {
    fetchMock().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: "facility-1",
          name: "Sunrise Medical Centre",
          slug: "sunrise-medical-centre",
          type: "hospital",
          country: "Nigeria",
          phone: "+234 800 000 0000",
          email: "admin@sunrise.test",
          modules: ["patients", "records", "dashboard"],
          created_at: "2026-05-31T10:00:00",
        }),
        { status: 200 }
      )
    );

    const workspace = await getFacilityWorkspace("sunrise-medical-centre");

    expect(fetchMock().mock.calls[0][0]).toBe(
      "/api/v1/facilities/workspace/sunrise-medical-centre"
    );
    expect(workspace?.selectedModules).toEqual(["reception", "records", "reports"]);
  });

  it("updates cached modules and notifies open workspace UI", () => {
    const listener = vi.fn();
    window.addEventListener(WORKSPACE_UPDATED_EVENT, listener);
    window.localStorage.setItem(
      "hispro.workspace.sunrise-medical-centre",
      JSON.stringify({
        facilityName: "Sunrise Medical Centre",
        facilityType: "hospital",
        country: "Nigeria",
        fullName: "Dr. Amina Yusuf",
        email: "admin@sunrise.test",
        phone: "+234 800 000 0000",
        selectedModules: ["reception", "records"],
        facilitySlug: "sunrise-medical-centre",
        createdAt: "2026-05-31T10:00:00",
      })
    );

    const workspace = updateCachedFacilityWorkspace("sunrise-medical-centre", {
      selectedModules: ["reception", "billing"],
    });

    expect(workspace?.selectedModules).toEqual(["reception", "billing"]);
    expect(
      JSON.parse(window.localStorage.getItem("hispro.workspace.sunrise-medical-centre") || "{}")
        .selectedModules
    ).toEqual(["reception", "billing"]);
    expect(listener).toHaveBeenCalledTimes(1);
    window.removeEventListener(WORKSPACE_UPDATED_EVENT, listener);
  });
});
