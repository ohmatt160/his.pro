import type { StaffRole } from "@/lib/facility-staff";

export type WorkspaceRole = StaffRole;

export const roleAllows = (
  role: string | undefined | null,
  allowedRoles?: WorkspaceRole[]
) => {
  if (!allowedRoles?.length) {
    return true;
  }
  return Boolean(role && allowedRoles.includes(role as WorkspaceRole));
};

export const routeRoles = {
  admin: ["admin", "branch_admin"],
  patients: ["admin", "branch_admin", "reception"],
  appointments: ["admin", "branch_admin", "reception", "doctor"],
  queue: ["admin", "branch_admin", "reception", "doctor", "nurse"],
  consultations: ["admin", "branch_admin", "doctor"],
  wards: ["admin", "branch_admin", "doctor", "nurse"],
  records: ["admin", "branch_admin", "doctor", "nurse"],
  billing: ["admin", "branch_admin", "reception"],
  laboratory: ["admin", "branch_admin", "lab"],
  pharmacy: ["admin", "branch_admin", "pharmacist"],
  radiology: ["admin", "branch_admin", "doctor"],
  inventory: ["admin", "branch_admin", "pharmacist"],
  reports: ["admin", "branch_admin"],
  alerts: ["admin", "branch_admin", "doctor", "nurse", "reception", "pharmacist", "lab"],
  chat: ["admin", "branch_admin", "doctor", "nurse", "reception", "pharmacist", "lab"],
} satisfies Record<string, WorkspaceRole[]>;
