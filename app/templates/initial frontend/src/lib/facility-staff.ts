import { apiClient, type AuthUser } from "@/api/client";
import {
  getCanonicalTenantUrl,
  getCurrentBranchSlugFromPath,
  getTenantPath,
  isCanonicalTenantHost,
  isValidCanonicalSubdomain,
} from "@/lib/tenant-routing";

export type StaffRole =
  | "admin"
  | "branch_admin"
  | "doctor"
  | "nurse"
  | "reception"
  | "pharmacist"
  | "lab"
  | "billing";

export type FacilityStaffAccount = {
  staffRecordId: string;
  facilitySlug: string;
  fullName: string;
  role: StaffRole;
  department: string;
  departmentId?: string | null;
  departmentIds?: string[];
  branchId?: string | null;
  branchIds?: string[];
  email: string;
  phone: string;
  loginId: string;
  password: string;
  temporaryPassword: string;
  mustChangePassword: boolean;
  status: "active" | "inactive";
  createdAt: string;
  createdBy?: string;
};

export type StaffSession = {
  facilitySlug: string;
  loginId: string;
  role: StaffRole;
};

export type AuthResponse = {
  access_token: string;
  refresh_token?: string;
  token_type: "bearer";
  user: AuthUser & {
    role: StaffRole;
  };
};

type BackendTokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};

type BackendUser = {
  id?: string;
  username: string;
  email?: string;
  role: string;
  first_name?: string | null;
  last_name?: string | null;
  facility_id?: string | null;
  facility_slug?: string | null;
  branch_id?: string | null;
  branch_ids?: string[] | null;
  branch_slug?: string | null;
  branch_slugs?: string[] | null;
};

const roleMetadata: Record<
  StaffRole,
  { label: string; prefix: string; department: string }
> = {
  admin: {
    label: "Main Facility Admin",
    prefix: "ADM",
    department: "Administration",
  },
  branch_admin: {
    label: "Branch Admin",
    prefix: "BADM",
    department: "Administration",
  },
  doctor: {
    label: "Doctor",
    prefix: "DOC",
    department: "Consultations",
  },
  nurse: {
    label: "Nurse",
    prefix: "NUR",
    department: "Nursing",
  },
  reception: {
    label: "Receptionist",
    prefix: "REC",
    department: "Front Desk",
  },
  pharmacist: {
    label: "Pharmacist",
    prefix: "PHA",
    department: "Pharmacy",
  },
  lab: {
    label: "Lab Staff",
    prefix: "LAB",
    department: "Laboratory",
  },
  billing: {
    label: "Billing Officer",
    prefix: "BIL",
    department: "Revenue & Billing",
  },
};

export const staffRoles = Object.keys(roleMetadata) as StaffRole[];

export const getStaffRoleLabel = (role: StaffRole) => roleMetadata[role].label;

export const getDefaultDepartmentForRole = (role: StaffRole) =>
  roleMetadata[role].department;

const getRolePrefix = (role: StaffRole) => roleMetadata[role].prefix;

const normalizeLoginValue = (value: string) => value.trim().toUpperCase();

const normalizeBackendRole = (role: string): StaffRole => {
  const normalized = role.toLowerCase();

  if (normalized === "branch_admin") {
    return "branch_admin";
  }

  if (normalized === "lab_tech") {
    return "lab";
  }

  if (normalized === "receptionist") {
    return "reception";
  }

  if (staffRoles.includes(normalized as StaffRole)) {
    return normalized as StaffRole;
  }

  return "reception";
};

const mapBackendUser = (user: BackendUser): AuthUser & { role: StaffRole } => {
  const role = normalizeBackendRole(user.role);
  const fullName = [user.first_name, user.last_name].filter(Boolean).join(" ");

  return {
    id: user.id,
    facilityId: user.facility_id || undefined,
    facilitySlug: user.facility_slug || "",
    branchId: user.branch_id || undefined,
    branchIds: user.branch_ids || [],
    branchSlug: user.branch_slug || undefined,
    branchSlugs: user.branch_slugs || [],
    loginId: user.username,
    role,
    fullName: fullName || user.username,
    email: user.email,
  };
};

export const getFacilityLoginPath = (facilitySlug: string) =>
  getTenantPath("/login", `/${facilitySlug}`);

export const getFacilityLoginLink = (facilitySlug: string) => {
  const origin =
    typeof window !== "undefined" ? window.location.origin : "https://his.pro";

  return isCanonicalTenantHost()
    ? `${origin}/login`
    : isValidCanonicalSubdomain(facilitySlug)
      ? getCanonicalTenantUrl(facilitySlug, "/login")
      : `${origin}/${encodeURIComponent(facilitySlug)}`;
};

export const getBranchLoginPath = (facilitySlug: string, branchSlug: string) =>
  getTenantPath(
    `/branches/${branchSlug}/login`,
    `/${facilitySlug}/branches/${branchSlug}/login`
  );

export const getBranchLoginLink = (facilitySlug: string, branchSlug: string) => {
  const origin =
    typeof window !== "undefined" ? window.location.origin : "https://his.pro";

  return isCanonicalTenantHost()
    ? `${origin}/branches/${branchSlug}/login`
    : isValidCanonicalSubdomain(facilitySlug)
      ? getCanonicalTenantUrl(facilitySlug, `/branches/${branchSlug}/login`)
      : `${origin}/${encodeURIComponent(facilitySlug)}/branches/${encodeURIComponent(branchSlug)}/login`;
};

export const getStaffPortalPath = (facilitySlug: string) =>
  getCurrentBranchSlugFromPath(facilitySlug)
    ? getBranchStaffPortalPath(
        facilitySlug,
        getCurrentBranchSlugFromPath(facilitySlug)
      )
    : getTenantPath("/portal", `/portal/${facilitySlug}`);

export const getBranchStaffPortalPath = (facilitySlug: string, branchSlug: string) =>
  getTenantPath(
    `/branches/${branchSlug}/portal`,
    `/${facilitySlug}/branches/${branchSlug}/portal`
  );

export const getStaffAccessPath = (facilitySlug: string) =>
  getCurrentBranchSlugFromPath(facilitySlug)
    ? getBranchStaffAccessPath(
        facilitySlug,
        getCurrentBranchSlugFromPath(facilitySlug)
      )
    : getTenantPath("/dashboard/staff", `/dashboard/${facilitySlug}/staff`);

export const getBranchStaffAccessPath = (facilitySlug: string, branchSlug: string) =>
  getTenantPath(
    `/branches/${branchSlug}/dashboard/staff`,
    `/${facilitySlug}/branches/${branchSlug}/dashboard/staff`
  );

export const authenticateStaff = async ({
  facilitySlug,
  branchSlug,
  login,
  password,
}: {
  facilitySlug: string;
  branchSlug?: string;
  login: string;
  password: string;
}) => {
  const query = new URLSearchParams({ facility_slug: facilitySlug });
  if (branchSlug) {
    query.set("branch_slug", branchSlug);
  }

  const auth = await apiClient.post<BackendTokenResponse>(
    `/auth/login?${query.toString()}`,
    {
      username: login,
      password,
    }
  );
  apiClient.setToken(auth.access_token);
  const user = await getProfile(auth.access_token);

  return {
    ...auth,
    user: {
      ...user,
      role: normalizeBackendRole(user.role),
    },
  } as AuthResponse;
};

export const getProfile = async (authToken?: string) =>
  apiClient
    .request<BackendUser>("/users/me", {
      method: "GET",
      authToken,
    })
    .then(mapBackendUser);

export const registerAdminUser = async ({
  username,
  email,
  password,
  fullName,
}: {
  username: string;
  email: string;
  password: string;
  fullName: string;
}) => {
  const [firstName, ...lastNameParts] = fullName.trim().split(/\s+/);

  return apiClient.post<BackendUser>("/auth/register", {
    username,
    email,
    password,
    role: "ADMIN",
    first_name: firstName || "Facility",
    last_name: lastNameParts.join(" ") || "Admin",
  });
};

export const getFacilityStaff = async (
  facilitySlug: string
): Promise<FacilityStaffAccount[]> =>
  apiClient.get<FacilityStaffAccount[]>(`/facilities/${facilitySlug}/staff`);

export const getFacilityClinicians = async (
  facilitySlug: string
): Promise<FacilityStaffAccount[]> =>
  apiClient.get<FacilityStaffAccount[]>(`/facilities/${facilitySlug}/clinicians`);

export const getStaffByLoginId = async (
  facilitySlug: string,
  loginId: string
): Promise<FacilityStaffAccount | null> => {
  try {
    return await apiClient.get<FacilityStaffAccount>(
      `/facilities/${facilitySlug}/staff/${normalizeLoginValue(loginId)}`
    );
  } catch {
    return null;
  }
};

export const createStaffAccount = async ({
  facilitySlug,
  fullName,
  role,
  department,
  email,
  phone,
  password,
  createdBy,
  departmentId,
  departmentIds,
  branchId,
  branchIds,
}: {
  facilitySlug: string;
  fullName: string;
  role: StaffRole;
  department?: string;
  departmentId?: string;
  departmentIds?: string[];
  branchId?: string;
  branchIds?: string[];
  email: string;
  phone?: string;
  password?: string;
  createdBy?: string;
}) => {
  const payload = {
    fullName,
    role,
    department: department || getDefaultDepartmentForRole(role),
    departmentId,
    departmentIds,
    branchId: branchId || departmentId,
    branchIds: branchIds || departmentIds,
    email: email.trim() ? email.trim().toLowerCase() : undefined,
    phone: phone?.trim() || undefined,
    password,
    createdBy,
  };

  return apiClient.post<FacilityStaffAccount>(
    `/facilities/${facilitySlug}/staff`,
    payload
  );
};

export const updateStaffAccount = async ({
  facilitySlug,
  staffRecordId,
  loginId,
  fullName,
  role,
  department,
  email,
  phone,
  password,
  mustChangePassword,
  isActive,
  departmentId,
  departmentIds,
  branchId,
  branchIds,
}: {
  facilitySlug: string;
  staffRecordId?: string;
  loginId?: string;
  fullName?: string;
  role?: StaffRole;
  department?: string;
  departmentId?: string;
  departmentIds?: string[];
  branchId?: string;
  branchIds?: string[];
  email?: string;
  phone?: string;
  password?: string;
  mustChangePassword?: boolean;
  isActive?: boolean;
}) => {
  const staffIdentifier = staffRecordId?.trim() || loginId?.trim();
  if (!staffIdentifier) {
    throw new Error("Staff account identifier is required.");
  }

  const payload = {
    fullName: fullName?.trim() || undefined,
    role,
    department: department?.trim() || undefined,
    departmentId,
    departmentIds,
    branchId: branchId || departmentId,
    branchIds: branchIds || departmentIds,
    email: email?.trim() ? email.trim().toLowerCase() : undefined,
    phone: phone?.trim() || undefined,
    password: password?.trim() || undefined,
    mustChangePassword,
    isActive,
  };

  return apiClient.put<FacilityStaffAccount>(
    `/facilities/${facilitySlug}/staff/${encodeURIComponent(staffIdentifier)}`,
    payload
  );
};

export const ensureAdminStaffAccount = async ({
  facilitySlug,
  fullName,
  email,
  phone,
  password,
}: {
  facilitySlug: string;
  fullName: string;
  email: string;
  phone?: string;
  password?: string;
}) => {
  const staff = await getFacilityStaff(facilitySlug);
  const existingAdmin = staff.find((member) => member.role === "admin");

  if (existingAdmin) {
    return existingAdmin;
  }

  return createStaffAccount({
    facilitySlug,
    fullName,
    role: "admin",
    department: getDefaultDepartmentForRole("admin"),
    email,
    phone,
    password,
  });
};
