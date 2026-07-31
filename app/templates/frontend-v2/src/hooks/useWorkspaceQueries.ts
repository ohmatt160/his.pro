import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import {
  getFacilityWorkspace,
  type SavedFacilityWorkspace,
} from "@/lib/facility-workspace";

export type FacilityBranch = {
  id: string;
  name: string;
  slug?: string;
  location?: string;
  modules?: string[];
  login_url_path?: string;
  dashboard_url_path?: string;
};

export type FacilityDetails = {
  id?: string;
  name: string;
  slug: string;
  type: string;
  country?: string | null;
  phone?: string | null;
  email?: string | null;
  modules?: string[];
  hospital_type?: string;
  departments?: FacilityBranch[];
  branches?: FacilityBranch[];
  created_at?: string;
};

export type DashboardStats = {
  patient_count: number;
  today_appointments: number;
  pending_lab_orders: number;
  pending_radiology_orders: number;
  low_inventory_items: number;
  active_alerts: number;
  active_queue_count: number;
};

export const workspaceQueryKeys = {
  workspace: (facilitySlug: string) => ["workspace", facilitySlug] as const,
  branches: (facilitySlug: string) => ["facility-branches", facilitySlug] as const,
  facility: (facilitySlug: string) => ["facility", facilitySlug] as const,
  dashboard: (facilitySlug: string, branchId: string) =>
    ["dashboard-stats", facilitySlug, branchId || "all"] as const,
  unreadMessages: (userId: string) => ["chat-unread", userId] as const,
};

export const useWorkspaceQuery = (facilitySlug: string) =>
  useQuery<SavedFacilityWorkspace | null>({
    queryKey: workspaceQueryKeys.workspace(facilitySlug),
    queryFn: () => getFacilityWorkspace(facilitySlug),
    enabled: Boolean(facilitySlug),
    staleTime: 15 * 60_000,
  });

export const useBranchesQuery = (facilitySlug: string, enabled = true) =>
  useQuery<FacilityBranch[]>({
    queryKey: workspaceQueryKeys.branches(facilitySlug),
    queryFn: () => apiClient.get<FacilityBranch[]>(`/facilities/${facilitySlug}/branches`),
    enabled: Boolean(facilitySlug) && enabled,
    staleTime: 15 * 60_000,
  });

export const useFacilityQuery = (facilitySlug: string, enabled = true) =>
  useQuery<FacilityDetails>({
    queryKey: workspaceQueryKeys.facility(facilitySlug),
    queryFn: () => apiClient.get<FacilityDetails>(`/facilities/${facilitySlug}`),
    enabled: Boolean(facilitySlug) && enabled,
    staleTime: 15 * 60_000,
  });

export const useDashboardStatsQuery = (
  facilitySlug: string,
  branchId = "",
  enabled = true
) =>
  useQuery<DashboardStats>({
    queryKey: workspaceQueryKeys.dashboard(facilitySlug, branchId),
    queryFn: () => {
      const branchQuery = branchId ? `&branch_id=${encodeURIComponent(branchId)}` : "";
      return apiClient.get<DashboardStats>(
        `/dashboard/stats?facility_slug=${encodeURIComponent(facilitySlug)}${branchQuery}`
      );
    },
    enabled: Boolean(facilitySlug) && enabled,
    staleTime: 5 * 60_000,
  });

export const useUnreadMessagesQuery = (userId: string, enabled = true) =>
  useQuery<{ unread_count: number }>({
    queryKey: workspaceQueryKeys.unreadMessages(userId),
    queryFn: () => apiClient.get<{ unread_count: number }>("/chat/unread-count"),
    enabled: Boolean(userId) && enabled,
    staleTime: 5 * 60_000,
  });
