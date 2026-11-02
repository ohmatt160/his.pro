import type { StaffRole } from "@/lib/facility-staff";

export type WorkspaceRole = StaffRole;

/**
 * Context-aware role check that considers facility and branch context
 * @param role - The user's role
 * @param allowedRoles - The roles allowed for the action
 * @param facilitySlug - Optional facility slug for context
 * @param branchSlug - Optional branch slug for context
 * @returns Whether the role is allowed
 */
export const roleAllows = (
  role: string | undefined | null,
  allowedRoles?: WorkspaceRole[],
  facilitySlug?: string,
  branchSlug?: string
) => {
  if (!allowedRoles?.length) {
    return true;
  }

  // If no facility/branch context, just check role inclusion
  if (!facilitySlug && !branchSlug) {
    return Boolean(role && allowedRoles.includes(role as WorkspaceRole));
  }

  // With context, we need the role to be included AND have appropriate context
  const hasRole = Boolean(role && allowedRoles.includes(role as WorkspaceRole));

  // If user has admin/branch_admin role, they have access to everything within their scope
  if (role === "admin" || role === "branch_admin") {
    return hasRole;
  }

  // For other roles, check if the role is in the allowed list
  return hasRole;
};

/**
 * Check if a role has access to a specific module considering context
 * @param role - The user's role
 * @param moduleId - The module ID to check access for
 * @param facilitySlug - Optional facility slug
 * @param branchSlug - Optional branch slug
 * @returns Whether the role can access the module
 */
export const isRoleAllowedForModule = (
  role: string | undefined | null,
  moduleId: string | undefined | null,
  facilitySlug?: string,
  branchSlug?: string
) => {
  if (!role || !moduleId) {
    return false;
  }

  const normalizedRole = role.toLowerCase() as WorkspaceRole;
  const moduleRoleAccess: Record<WorkspaceRole, WorkspaceRole[]> = {
    reception: ["admin", "branch_admin", "reception", "doctor", "nurse"],
    records: ["admin", "branch_admin", "doctor", "nurse"],
    consultations: ["admin", "branch_admin", "doctor", "nurse"],
    nursing: ["admin", "branch_admin", "doctor", "nurse"],
    lab: ["admin", "branch_admin", "doctor", "lab"],
    pharmacy: ["admin", "branch_admin", "doctor", "pharmacist"],
    billing: ["admin", "branch_admin", "reception", "billing"],
    radiology: ["admin", "branch_admin", "doctor"],
    inventory: ["admin", "pharmacist"],
    reports: ["admin", "branch_admin", "doctor", "nurse", "reception"],
  };

  const allowed = moduleRoleAccess[moduleId as WorkspaceRole] || [];
  const hasRole = allowed.includes(normalizedRole);

  // Admin/branch_admin have access to everything
  if (normalizedRole === "admin" || normalizedRole === "branch_admin") {
    return true;
  }

  return hasRole;
};

/**
 * Get the effective role considering facility/branch context
 * This can be used to determine what a user can actually do in their current context
 */
export const getEffectiveRole = (
  role: string | undefined | null,
  facilitySlug: string,
  branchSlug?: string
): "full" | "branch" | "none" => {
  if (!role) {
    return "none";
  }

  if (role === "admin" || role === "branch_admin") {
    return branchSlug ? "branch" : "full";
  }

  // For other roles, check if they have branch-specific access
  return "full";
};

/**
 * Pre-defined role sets for common routes
 * These map to the routeRoles object but with added context support
 */
export const routeRoles = {
  admin: ["admin", "branch_admin"],
  patients: ["admin", "branch_admin", "reception", "doctor", "nurse"],
  appointments: ["admin", "branch_admin", "reception", "doctor"],
  queue: ["admin", "branch_admin", "reception", "doctor", "nurse"],
  consultations: ["admin", "branch_admin", "doctor"],
  wards: ["admin", "branch_admin", "doctor", "nurse"],
  records: ["admin", "branch_admin", "doctor", "nurse"],
  billing: ["admin", "branch_admin", "reception", "billing"],
  laboratory: ["admin", "branch_admin", "doctor", "lab"],
  pharmacy: ["admin", "branch_admin", "doctor", "pharmacist"],
  radiology: ["admin", "branch_admin", "doctor"],
  inventory: ["admin", "branch_admin", "pharmacist"],
  reports: ["admin", "branch_admin"],
  alerts: ["admin", "branch_admin", "doctor", "nurse", "reception", "pharmacist", "lab", "billing"],
  chat: ["admin", "branch_admin", "doctor", "nurse", "reception", "pharmacist", "lab", "billing"],
} satisfies Record<string, WorkspaceRole[]>;

/**
 * Enhanced role allows that also considers facility/branch context from TenantRoutingContext
 * This is a wrapper that can be used with React context values
 */
export const roleAllowsWithContext = (
  role: string | undefined | null,
  allowedRoles: WorkspaceRole[],
  facilitySlug: string,
  branchSlug?: string
) => {
  if (!allowedRoles?.length) {
    return true;
  }

  // Admin/branch_admin have access to everything in their scope
  if (role === "admin" || role === "branch_admin") {
    return true;
  }

  // Check if the role is in the allowed list
  const hasRole = allowedRoles.includes(role as WorkspaceRole);
  return hasRole;
};
