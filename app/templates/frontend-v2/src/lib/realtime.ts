import type { QueryClient } from "@tanstack/react-query";
import type { AuthUser } from "@/api/client";
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

export const getRealtimeWebSocketUrl = () => {
  const apiUrl = new URL(getApiBaseUrl(), window.location.origin);
  const protocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
  const path = `${apiUrl.pathname.replace(/\/+$/, "")}/realtime/ws`;
  return `${protocol}//${apiUrl.host}${path}`;
};

export const dispatchRealtimeEvent = (event: RealtimeEvent) => {
  window.dispatchEvent(new CustomEvent<RealtimeEvent>(HISPRO_REALTIME_EVENT, { detail: event }));
};

export const realtimeEventMatchesUserScope = (
  event: RealtimeEvent,
  user: AuthUser,
) => {
  if (!event.facility_slug || event.facility_slug !== user.facilitySlug) {
    return false;
  }

  if (event.user_id && (!user.id || String(event.user_id) !== String(user.id))) {
    return false;
  }

  const normalizedRole = user.role.toLowerCase();
  if (
    event.roles?.length &&
    !event.roles.some((role) => role.toLowerCase() === normalizedRole)
  ) {
    return false;
  }

  if (event.branch_id && normalizedRole !== "admin") {
    const allowedBranchIds = new Set(
      [user.branchId, ...(user.branchIds || [])]
        .filter(Boolean)
        .map(String),
    );
    if (!allowedBranchIds.has(String(event.branch_id))) {
      return false;
    }
  }

  return true;
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
