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
  admin: ["admin"],
  patients: ["admin", "reception"],
  appointments: ["admin", "reception", "doctor"],
  queue: ["admin", "reception", "doctor", "nurse"],
  consultations: ["admin", "doctor"],
  wards: ["admin", "doctor", "nurse"],
  records: ["admin", "doctor", "nurse"],
  billing: ["admin", "reception"],
  laboratory: ["admin", "lab"],
  pharmacy: ["admin", "pharmacist"],
  radiology: ["admin", "doctor"],
  inventory: ["admin", "pharmacist"],
  reports: ["admin"],
  alerts: ["admin", "doctor", "nurse", "reception", "pharmacist", "lab"],
} satisfies Record<string, WorkspaceRole[]>;
