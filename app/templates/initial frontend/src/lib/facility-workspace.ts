import { apiClient } from "@/api/client";

export type FacilityWorkspaceData = {
  facilityName: string;
  facilityType: string;
  country: string;
  fullName: string;
  email: string;
  phone: string;
  adminPassword?: string;
  selectedModules: string[];
};

export type SavedFacilityWorkspace = FacilityWorkspaceData & {
  facilitySlug: string;
  createdAt: string;
};

type BackendFacility = {
  id: string;
  name: string;
  slug: string;
  type: string;
  country?: string | null;
  phone?: string | null;
  email?: string | null;
  modules?: string[];
  created_at?: string;
};

type BackendTokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};

const WORKSPACE_STORAGE_PREFIX = "hispro.workspace.";

export const createFacilitySlug = (facilityName: string) =>
  facilityName
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "my-facility";

export const getFacilityDashboardPath = (facilitySlug: string) =>
  `/dashboard/${facilitySlug}`;

export const getFacilityReadyPath = (facilitySlug: string) =>
  `/workspace-ready/${facilitySlug}`;

export const getFacilityPlatformLink = (facilitySlug: string) => {
  const origin =
    typeof window !== "undefined" ? window.location.origin : "https://his.pro";

  return `${origin}/${facilitySlug}`;
};

const getWorkspaceStorageKey = (facilitySlug: string) =>
  `${WORKSPACE_STORAGE_PREFIX}${facilitySlug}`;

const cacheWorkspace = (workspace: SavedFacilityWorkspace) => {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(
    getWorkspaceStorageKey(workspace.facilitySlug),
    JSON.stringify(workspace)
  );
};

const getCachedWorkspace = (facilitySlug: string) => {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.localStorage.getItem(getWorkspaceStorageKey(facilitySlug));
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as SavedFacilityWorkspace;
  } catch {
    window.localStorage.removeItem(getWorkspaceStorageKey(facilitySlug));
    return null;
  }
};

const splitFullName = (fullName: string) => {
  const [firstName, ...lastNameParts] = fullName.trim().split(/\s+/);

  return {
    firstName: firstName || "Facility",
    lastName: lastNameParts.join(" ") || "Admin",
  };
};

const mapBackendFacility = (
  facility: BackendFacility,
  fallback: FacilityWorkspaceData
): SavedFacilityWorkspace => ({
  facilityName: facility.name,
  facilityType: facility.type,
  country: facility.country || fallback.country || "",
  fullName: fallback.fullName,
  email: facility.email || fallback.email,
  phone: facility.phone || fallback.phone,
  selectedModules: facility.modules?.length
    ? facility.modules
    : fallback.selectedModules,
  facilitySlug: facility.slug,
  createdAt: facility.created_at || new Date().toISOString(),
});

export const saveFacilityWorkspace = async (
  data: FacilityWorkspaceData
): Promise<SavedFacilityWorkspace> => {
  const facilitySlug = createFacilitySlug(data.facilityName);
  const { firstName, lastName } = splitFullName(data.fullName);
  const username = `${facilitySlug}-admin`;
  if (!data.adminPassword) {
    throw new Error("Admin password is required to create a facility workspace.");
  }

  const email = data.email.trim().toLowerCase();
  const auth = await apiClient.post<BackendTokenResponse>("/auth/ensure", {
    username,
    email,
    password: data.adminPassword,
    role: "ADMIN",
    first_name: firstName,
    last_name: lastName,
  });

  const facility = await apiClient.request<BackendFacility>("/facilities/ensure", {
    method: "POST",
    authToken: auth.access_token,
    body: {
      name: data.facilityName,
      type: data.facilityType,
      country: data.country,
      phone: data.phone,
      email,
      modules: data.selectedModules,
      settings: {
        administrator: {
          fullName: data.fullName,
          username,
        },
      },
    },
  });
  const workspace = mapBackendFacility(facility, data);

  cacheWorkspace(workspace);
  return workspace;
};

export const getFacilityWorkspace = async (
  facilitySlug: string
): Promise<SavedFacilityWorkspace | null> => {
  const cachedWorkspace = getCachedWorkspace(facilitySlug);
  if (cachedWorkspace) {
    return cachedWorkspace;
  }

  try {
    const facility = await apiClient.get<BackendFacility>(
      `/facilities/${facilitySlug}`
    );
    const workspace = mapBackendFacility(facility, {
      facilityName: facility.name,
      facilityType: facility.type,
      country: facility.country || "",
      fullName: "Admin",
      email: facility.email || "",
      phone: facility.phone || "",
      selectedModules: facility.modules || [],
    });

    cacheWorkspace(workspace);
    return workspace;
  } catch {
    return null;
  }
};
