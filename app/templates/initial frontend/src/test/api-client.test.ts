import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  apiClient,
  clearToken,
  clearUser,
  getUser,
  post,
  request,
  setToken,
  setUser,
  type AuthUser,
} from "../api/client";

const getFetchCall = () => {
  const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
  return fetchMock.mock.calls[0] as [string, RequestInit];
};

const getFetchMock = () => fetch as unknown as ReturnType<typeof vi.fn>;

describe("api client", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it("persists and clears auth state", () => {
    const user: AuthUser = {
      facilitySlug: "sunrise-clinic",
      loginId: "ADM-001",
      role: "admin",
      fullName: "Dr. Amina Yusuf",
      email: "amina@example.com",
    };

    setToken("token-123");
    setUser(user);

    expect(apiClient.getToken()).toBe("token-123");
    expect(getUser()).toEqual(user);
    expect(apiClient.isSignedIn()).toBe(true);

    clearToken();
    clearUser();

    expect(apiClient.getToken()).toBeNull();
    expect(getUser()).toBeNull();
    expect(apiClient.isSignedIn()).toBe(false);
  });

  it("clears corrupt stored user data", () => {
    window.localStorage.setItem("hispro.auth.user", "{bad-json");

    expect(getUser()).toBeNull();
    expect(window.localStorage.getItem("hispro.auth.user")).toBeNull();
  });

  it("sends JSON requests with auth headers", async () => {
    setToken("token-123");
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    );

    await post<{ ok: boolean }>("/facilities", {
      facilityName: "Sunrise Clinic",
    });

    const [url, options] = getFetchCall();
    const headers = options.headers as Headers;

    expect(url).toBe("/api/v1/facilities");
    expect(options.method).toBe("POST");
    expect(headers.get("Authorization")).toBe("Bearer token-123");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(options.body).toBe(JSON.stringify({ facilityName: "Sunrise Clinic" }));
  });

  it("can use a one-request auth token without persisting it", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    );

    await request<{ ok: boolean }>("/facilities/ensure", {
      method: "POST",
      authToken: "setup-token",
      body: { name: "Sunrise Clinic" },
    });

    const [, options] = getFetchCall();
    const headers = options.headers as Headers;

    expect(headers.get("Authorization")).toBe("Bearer setup-token");
    expect(window.localStorage.getItem("hispro.auth.token")).toBeNull();
  });

  it("keeps absolute request URLs untouched", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), { status: 200 })
    );

    await request("https://api.example.com/facilities");

    const [url] = getFetchCall();

    expect(url).toBe("https://api.example.com/facilities");
  });

  it("preserves browser-native request bodies", async () => {
    const formData = new FormData();
    formData.append("avatar", new Blob(["image-bytes"]), "avatar.png");
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }));

    await request<void>("/uploads", {
      method: "POST",
      body: formData,
    });

    const [, options] = getFetchCall();
    const headers = options.headers as Headers;

    expect(options.body).toBe(formData);
    expect(headers.has("Content-Type")).toBe(false);
  });

  it("uses API error details when available", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Invalid login" }), {
        status: 401,
        statusText: "Unauthorized",
      })
    );

    await expect(request("/auth/login", { method: "POST" })).rejects.toThrow(
      "Invalid login"
    );
  });

  it("formats structured validation errors without dumping raw JSON", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: {
            message: "Validation error",
            code: 2001,
            status: 400,
            details: [
              {
                loc: ["body", "email"],
                msg: "value is not a valid email address",
              },
            ],
          },
        }),
        { status: 400 }
      )
    );

    await expect(request("/facilities/demo/staff", { method: "POST" })).rejects.toThrow(
      "Please check email and try again."
    );
  });

  it("refreshes once and retries protected requests after a 401", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Token expired" }), {
          status: 401,
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: "refreshed-token",
            refresh_token: "rotated-refresh",
            token_type: "bearer",
          }),
          { status: 200 }
        )
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ staff: [] }), { status: 200 })
      );

    const result = await request<{ staff: unknown[] }>("/facilities/demo/staff");

    expect(result.staff).toEqual([]);
    expect(fetch).toHaveBeenCalledTimes(3);
    expect(getFetchMock().mock.calls[1][0]).toBe("/api/v1/auth/refresh");

    const retryHeaders = getFetchMock().mock.calls[2][1].headers as Headers;
    expect(retryHeaders.get("Authorization")).toBe("Bearer refreshed-token");
    expect(apiClient.getToken()).toBe("refreshed-token");
  });

  it("clears auth and emits an expiry event when refresh fails", async () => {
    const expiredListener = vi.fn();
    window.addEventListener("hispro:auth-expired", expiredListener);
    setToken("expired-token");
    setUser({
      facilitySlug: "sunrise-clinic",
      loginId: "ADM-001",
      role: "admin",
      fullName: "Admin",
    });

    vi.mocked(fetch)
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Expired" }), { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Invalid refresh" }), { status: 401 }));

    await expect(request("/patients")).rejects.toThrow("Expired");

    expect(apiClient.getToken()).toBeNull();
    expect(apiClient.getUser()).toBeNull();
    expect(expiredListener).toHaveBeenCalled();
    window.removeEventListener("hispro:auth-expired", expiredListener);
  });

  it("rejects successful responses with invalid JSON", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response("not-json", { status: 200 })
    );

    await expect(request("/broken-response")).rejects.toThrow(
      "API response was not valid JSON"
    );
  });
});
