import type { QueryClient } from "@tanstack/react-query";
import { workspaceQueryKeys } from "@/hooks/useWorkspaceQueries";

export const HISPRO_REALTIME_EVENT = "hispro:realtime-event";

export type RealtimeEvent = {
  id?: string;
  type: string;
  facility_slug?: string;
  branch_id?: string | null;
  user_id?: string | null;
  roles?: string[];
  modules?: string[];
  resource_id?: string | null;
  payload?: Record<string, unknown>;
  occurred_at?: string;
};

const getApiBaseUrl = () => {
  const configuredUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "");
  return configuredUrl || "/api/v1";
};

const configuredRealtimeEndpoint = () => {
  const configuredUrl = import.meta.env.VITE_REALTIME_WS_URL?.trim();
  if (configuredUrl) {
    const endpoint = new URL(configuredUrl, window.location.origin);
    if (!["ws:", "wss:"].includes(endpoint.protocol)) {
      return null;
    }
    return endpoint;
  }

  // Vite can proxy WebSocket upgrades locally. Vercel's HTTP rewrite cannot, so
  // production must opt in with a separately deployed WebSocket endpoint.
  if (!import.meta.env.DEV) {
    return null;
  }

  const apiUrl = new URL(getApiBaseUrl(), window.location.origin);
  apiUrl.protocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
  apiUrl.pathname = `${apiUrl.pathname.replace(/\/+$/, "")}/realtime/ws`;
  apiUrl.search = "";
  apiUrl.hash = "";
  return apiUrl;
};

export const getRealtimeWebSocketUrl = (ticket?: string) => {
  const endpoint = configuredRealtimeEndpoint();
  if (!endpoint) {
    return null;
  }

  if (ticket) {
    endpoint.searchParams.set("ticket", ticket);
  }
  return endpoint.toString();
};

export const dispatchRealtimeEvent = (event: RealtimeEvent) => {
  window.dispatchEvent(new CustomEvent<RealtimeEvent>(HISPRO_REALTIME_EVENT, { detail: event }));
};

export const invalidateRealtimeQueries = (
  queryClient: QueryClient,
  event: RealtimeEvent
) => {
  const facilitySlug = event.facility_slug;
  if (!facilitySlug || event.type.startsWith("system.")) {
    return;
  }

  queryClient.invalidateQueries({
    predicate: (query) => {
      const [key, slug] = query.queryKey;
      if (slug !== facilitySlug) {
        return false;
      }
      return key === "dashboard-stats" || key === "facility" || key === "facility-branches";
    },
  });

  if (event.type.startsWith("facility.") || event.type.startsWith("branch.")) {
    queryClient.invalidateQueries({ queryKey: workspaceQueryKeys.workspace(facilitySlug) });
    queryClient.invalidateQueries({ queryKey: workspaceQueryKeys.branches(facilitySlug) });
    queryClient.invalidateQueries({ queryKey: workspaceQueryKeys.facility(facilitySlug) });
  }

  if (event.type.startsWith("alert.") || event.type.startsWith("chat.")) {
    queryClient.invalidateQueries({
      predicate: (query) => query.queryKey[0] === "chat-unread",
    });
  }
};
