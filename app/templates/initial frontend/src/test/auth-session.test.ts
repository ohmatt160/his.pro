import { describe, expect, it } from "vitest";
import { describeSessionDevice, type ActiveSession } from "../lib/auth-session";

const session = (userAgent: string): ActiveSession => ({
  id: "session-1",
  user_agent: userAgent,
  ip_address: "127.0.0.1",
  last_seen_at: "2026-06-02T10:00:00",
  expires_at: "2026-06-09T10:00:00",
  is_current: true,
});

describe("auth session helpers", () => {
  it("describes common browser user agents for the settings screen", () => {
    expect(describeSessionDevice(session("Mozilla/5.0 Chrome/125.0"))).toBe(
      "Chrome browser"
    );
    expect(describeSessionDevice(session("Mozilla/5.0 Firefox/127.0"))).toBe(
      "Firefox browser"
    );
  });

  it("falls back when user agent is missing", () => {
    expect(describeSessionDevice({ ...session(""), user_agent: null })).toBe(
      "Unknown device"
    );
  });
});
