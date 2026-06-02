import { apiClient } from "@/api/client";
import { getProfile } from "@/lib/facility-staff";

export type ActiveSession = {
  id: string;
  user_agent?: string | null;
  ip_address?: string | null;
  last_seen_at: string;
  expires_at: string;
  is_current: boolean;
};

type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};

export const refreshProfile = async () => {
  const refreshed = await apiClient.post<TokenResponse>("/auth/refresh");
  return getProfile(refreshed.access_token);
};

export const getActiveSessions = () =>
  apiClient.get<ActiveSession[]>("/auth/sessions");

export const logoutEverywhere = () =>
  apiClient.post<{ message: string }>("/auth/logout-everywhere");

export const describeSessionDevice = (session: ActiveSession) => {
  const agent = session.user_agent || "Unknown device";
  if (/Chrome/i.test(agent)) return "Chrome browser";
  if (/Firefox/i.test(agent)) return "Firefox browser";
  if (/Safari/i.test(agent)) return "Safari browser";
  if (/Edg/i.test(agent)) return "Edge browser";
  return agent.slice(0, 80);
};
