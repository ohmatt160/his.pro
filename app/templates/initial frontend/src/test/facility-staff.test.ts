import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { authenticateStaff } from "../lib/facility-staff";

const fetchMock = () => fetch as unknown as ReturnType<typeof vi.fn>;

describe("facility staff authentication", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses the fresh login token to load the profile without persisting it", async () => {
    fetchMock()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: "fresh-access-token",
            refresh_token: "refresh-token",
            token_type: "bearer",
          }),
          { status: 200 }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            id: "user-1",
            username: "sunrise-medical-centre-admin",
            email: "admin@sunrise.test",
            role: "ADMIN",
            first_name: "Amina",
            last_name: "Yusuf",
            facility_slug: "sunrise-medical-centre",
          }),
          { status: 200 }
        )
      );

    const auth = await authenticateStaff({
      facilitySlug: "sunrise-medical-centre",
      login: "admin@sunrise.test",
      password: "Correct2026",
    });

    expect(auth.user.loginId).toBe("sunrise-medical-centre-admin");
    expect(fetchMock()).toHaveBeenCalledTimes(2);

    const profileRequest = fetchMock().mock.calls[1][1] as RequestInit;
    const profileHeaders = profileRequest.headers as Headers;
    expect(profileHeaders.get("Authorization")).toBe("Bearer fresh-access-token");
    expect(window.localStorage.getItem("hispro.auth.token")).toBeNull();
  });
});
