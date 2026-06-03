import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  getFacilityWorkspace,
  getFacilityPlatformLink,
  saveFacilityWorkspace,
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

  it("ensures an admin, creates a facility, caches the workspace, and leaves login required", async () => {
    fetchMock()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: "access-token",
            refresh_token: "refresh-token",
            token_type: "bearer",
          }),
          { status: 200 }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: "facility-1",
            name: "Sunrise Medical Centre",
            slug: "sunrise-medical-centre",
            type: "hospital",
            country: "Nigeria",
            phone: "+234 800 000 0000",
            email: "admin@sunrise.test",
            modules: ["reception", "records"],
            created_at: "2026-05-31T10:00:00",
          }),
          { status: 201 }
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

    expect(fetchMock()).toHaveBeenCalledTimes(2);
    expect(fetchMock().mock.calls[0][0]).toBe("/api/v1/auth/ensure");
    expect(fetchMock().mock.calls[0][1].body).toBe(
      JSON.stringify({
        username: "sunrise-medical-centre-admin",
        email: "admin@sunrise.test",
        password: "Password1",
        role: "ADMIN",
        first_name: "Dr.",
        last_name: "Amina Yusuf",
      })
    );
    expect(fetchMock().mock.calls[1][0]).toBe("/api/v1/facilities/ensure");
    expect(fetchMock().mock.calls[1][1].body).toBe(
      JSON.stringify({
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
      })
    );
    expect(workspace.facilitySlug).toBe("sunrise-medical-centre");
    expect(fetchMock().mock.calls[1][1].headers.get("Authorization")).toBe(
      "Bearer access-token"
    );
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
});
