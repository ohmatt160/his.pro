import { apiClient, type AuthUser } from "@/api/client";

export type StaffRole =
  | "admin"
  | "doctor"
  | "nurse"
  | "reception"
  | "pharmacist"
  | "lab";

export type FacilityStaffAccount = {
  staffRecordId: string;
  facilitySlug: string;
  fullName: string;
  role: StaffRole;
  department: string;
  email: string;
  phone: string;
  loginId: string;
  password: string;
  temporaryPassword: string;
  mustChangePassword: boolean;
  status: "active";
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
  facility_slug?: string | null;
};

const roleMetadata: Record<
  StaffRole,
  { label: string; prefix: string; department: string }
> = {
  admin: {
    label: "Facility Admin",
    prefix: "ADM",
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
};

export const staffRoles = Object.keys(roleMetadata) as StaffRole[];

export const getStaffRoleLabel = (role: StaffRole) => roleMetadata[role].label;

export const getDefaultDepartmentForRole = (role: StaffRole) =>
  roleMetadata[role].department;

const getRolePrefix = (role: StaffRole) => roleMetadata[role].prefix;

const normalizeLoginValue = (value: string) => value.trim().toUpperCase();

const normalizeBackendRole = (role: string): StaffRole => {
  const normalized = role.toLowerCase();

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
    facilitySlug: user.facility_slug || "",
    loginId: user.username,
    role,
    fullName: fullName || user.username,
    email: user.email,
  };
};

export const getFacilityLoginPath = (facilitySlug: string) =>
  `/${facilitySlug}`;

export const getFacilityLoginLink = (facilitySlug: string) => {
  const origin =
    typeof window !== "undefined" ? window.location.origin : "https://his.pro";

  return `${origin}${getFacilityLoginPath(facilitySlug)}`;
};

export const getStaffPortalPath = (facilitySlug: string) =>
  `/portal/${facilitySlug}`;

export const getStaffAccessPath = (facilitySlug: string) =>
  `/dashboard/${facilitySlug}/staff`;

export const authenticateStaff = async ({
  facilitySlug,
  login,
  password,
}: {
  facilitySlug: string;
  login: string;
  password: string;
}) => {
  const auth = await apiClient.post<BackendTokenResponse>(
    `/auth/login?facility_slug=${encodeURIComponent(facilitySlug)}`,
    {
      username: login,
      password,
    }
  );
  const user = await getProfile();

  return {
    ...auth,
    user: {
      ...user,
      role: normalizeBackendRole(user.role),
    },
  } as AuthResponse;
};

export const getProfile = async () =>
  apiClient
    .get<BackendUser>("/users/me")
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
): Promise<FacilityStaffAccount[]> => {
  try {
    return await apiClient.get<FacilityStaffAccount[]>(
      `/facilities/${facilitySlug}/staff`
    );
  } catch {
    return [];
  }
};

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
}: {
  facilitySlug: string;
  fullName: string;
  role: StaffRole;
  department?: string;
  email: string;
  phone?: string;
  password?: string;
  createdBy?: string;
}) => {
  const payload = {
    fullName,
    role,
    department: department || getDefaultDepartmentForRole(role),
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
