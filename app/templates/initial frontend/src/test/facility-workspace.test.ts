import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { saveFacilityWorkspace } from "../lib/facility-workspace";

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

  it("ensures an admin session, creates a facility, and caches the workspace", async () => {
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
        facility_slug: "sunrise-medical-centre",
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
    expect(window.localStorage.getItem("hispro.auth.token")).toBe("access-token");
    expect(JSON.parse(window.localStorage.getItem("hispro.auth.user") || "{}")).toMatchObject({
      facilitySlug: "sunrise-medical-centre",
      loginId: "sunrise-medical-centre-admin",
      role: "admin",
    });
  });
});
