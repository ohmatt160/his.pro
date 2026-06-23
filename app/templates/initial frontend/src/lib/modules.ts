import {
  Activity,
  BedDouble,
  CalendarDays,
  FileHeart,
  FlaskConical,
  Package,
  Pill,
  Receipt,
  ScanLine,
  Stethoscope,
  Users,
  type LucideIcon,
} from "lucide-react";

export type FacilityModuleId =
  | "reception"
  | "records"
  | "consultations"
  | "nursing"
  | "lab"
  | "pharmacy"
  | "billing"
  | "radiology"
  | "inventory"
  | "reports";

export type ModuleAccessRole =
  | "admin"
  | "branch_admin"
  | "doctor"
  | "nurse"
  | "reception"
  | "pharmacist"
  | "lab";

export type FacilityModule = {
  id: FacilityModuleId;
  label: string;
  description: string;
  icon: LucideIcon;
  primaryPath?: string;
};

export const moduleCatalog: FacilityModule[] = [
  {
    id: "reception",
    label: "Reception & Registration",
    description: "Patient registration, appointments, queues, and check-in.",
    icon: Users,
    primaryPath: "queue",
  },
  {
    id: "records",
    label: "Shared Patient Record",
    description: "One longitudinal patient chart shared across every department.",
    icon: FileHeart,
    primaryPath: "records",
  },
  {
    id: "consultations",
    label: "Doctors & Consultations",
    description: "Consult notes, diagnoses, treatment plans, and clinical orders.",
    icon: Stethoscope,
    primaryPath: "consultations",
  },
  {
    id: "nursing",
    label: "Nursing & Wards",
    description: "Vitals, nursing notes, medication rounds, and inpatient handoff.",
    icon: BedDouble,
    primaryPath: "wards",
  },
  {
    id: "lab",
    label: "Laboratory",
    description: "Test ordering, sample tracking, and result delivery.",
    icon: FlaskConical,
    primaryPath: "laboratory",
  },
  {
    id: "pharmacy",
    label: "Pharmacy",
    description: "Prescriptions, dispensing, and medication tracking.",
    icon: Pill,
    primaryPath: "pharmacy",
  },
  {
    id: "billing",
    label: "Billing & Claims",
    description: "Invoices, payments, and insurance workflow.",
    icon: Receipt,
    primaryPath: "billing",
  },
  {
    id: "radiology",
    label: "Radiology",
    description: "Imaging requests, reports, and scan workflow.",
    icon: ScanLine,
    primaryPath: "radiology",
  },
  {
    id: "inventory",
    label: "Inventory & Stores",
    description: "Stock control for drugs, consumables, and supplies.",
    icon: Package,
    primaryPath: "inventory",
  },
  {
    id: "reports",
    label: "Reports",
    description: "Operational, clinical, queue, and revenue summaries.",
    icon: Activity,
    primaryPath: "reports",
  },
];

export const moduleAliases: Record<string, FacilityModuleId> = {
  appointments: "reception",
  patients: "reception",
  medical_records: "records",
  dashboard: "reports",
};

export const moduleIds = moduleCatalog.map((module) => module.id);

export const defaultModulesByFacilityType: Record<string, FacilityModuleId[]> = {
  clinic: ["reception", "records", "consultations", "pharmacy", "billing"],
  hospital: [
    "reception",
    "records",
    "consultations",
    "nursing",
    "lab",
    "pharmacy",
    "billing",
    "radiology",
    "inventory",
    "reports",
  ],
  lab: ["reception", "records", "lab", "billing", "inventory", "reports"],
  pharmacy: ["pharmacy", "inventory", "billing", "reports"],
};

export const normalizeModules = (modules?: string[] | null) => {
  const normalized: FacilityModuleId[] = [];

  for (const rawModule of modules || []) {
    const module = (rawModule || "").trim().toLowerCase();
    const id = moduleAliases[module] || (module as FacilityModuleId);
    if (moduleIds.includes(id) && !normalized.includes(id)) {
      normalized.push(id);
    }
  }

  return normalized;
};

export const getDefaultModules = (facilityType: string) =>
  defaultModulesByFacilityType[facilityType] ||
  defaultModulesByFacilityType.hospital;

export const getModuleById = (id: string) =>
  moduleCatalog.find((module) => module.id === id);

export const isModuleEnabled = (
  modules: string[] | undefined | null,
  moduleId: FacilityModuleId
) => normalizeModules(modules).includes(moduleId);

export const getModulePath = (
  facilitySlug: string,
  moduleId: FacilityModuleId
) => {
  const module = getModuleById(moduleId);
  return module?.primaryPath ? `/dashboard/${facilitySlug}/${module.primaryPath}` : "";
};

export const routeModuleMap: Record<string, FacilityModuleId> = {
  patients: "reception",
  appointments: "reception",
  queue: "reception",
  records: "records",
  consultations: "consultations",
  wards: "nursing",
  laboratory: "lab",
  pharmacy: "pharmacy",
  billing: "billing",
  radiology: "radiology",
  inventory: "inventory",
  suppliers: "inventory",
  reports: "reports",
};

export const moduleRoleAccess: Record<FacilityModuleId, ModuleAccessRole[]> = {
  reception: ["admin", "branch_admin", "reception", "doctor", "nurse"],
  records: ["admin", "branch_admin", "doctor", "nurse"],
  consultations: ["admin", "branch_admin", "doctor", "nurse"],
  nursing: ["admin", "branch_admin", "doctor", "nurse"],
  lab: ["admin", "branch_admin", "doctor", "lab"],
  pharmacy: ["admin", "branch_admin", "doctor", "pharmacist"],
  billing: ["admin", "branch_admin", "reception"],
  radiology: ["admin", "branch_admin", "doctor"],
  inventory: ["admin", "pharmacist"],
  reports: ["admin", "branch_admin", "doctor", "nurse", "reception"],
};

export const isRoleAllowedForModule = (
  role: string | undefined | null,
  moduleId: FacilityModuleId
) => {
  if (!role) {
    return false;
  }

  const normalizedRole = role.toLowerCase() as ModuleAccessRole;
  return moduleRoleAccess[moduleId]?.includes(normalizedRole) || false;
};

export const getRouteModuleId = (pathOrLabel: string) => {
  const normalized = pathOrLabel.toLowerCase();
  const segment = normalized.split("/").filter(Boolean).pop() || normalized;

  if (routeModuleMap[segment]) {
    return routeModuleMap[segment];
  }

  if (normalized.includes("shared") && normalized.includes("record")) return "records";
  if (normalized.includes("medical record")) return "records";
  if (normalized.includes("patient records")) return "records";
  if (normalized.includes("patient")) return "reception";
  if (normalized.includes("schedule") || normalized.includes("appointment")) return "reception";
  if (normalized.includes("consult")) return "consultations";
  if (normalized.includes("ward") || normalized.includes("bed") || normalized.includes("handover")) return "nursing";
  if (normalized.includes("task") || normalized.includes("queue") || normalized.includes("check-in") || normalized.includes("arrival")) return "reception";
  if (normalized.includes("prescription") || normalized.includes("medication") || normalized.includes("dispense")) return "pharmacy";
  if (normalized.includes("lab") || normalized.includes("test") || normalized.includes("sample") || normalized.includes("result") || normalized.includes("quality")) return "lab";
  if (normalized.includes("record") || normalized.includes("note") || normalized.includes("vital")) return "records";
  if (normalized.includes("stock") || normalized.includes("inventory")) return "inventory";
  if (normalized.includes("billing") || normalized.includes("claim") || normalized.includes("payment") || normalized.includes("coverage")) return "billing";
  if (normalized.includes("report")) return "reports";

  return null;
};

export const canAccessModule = ({
  modules,
  moduleId,
  role,
}: {
  modules: string[] | undefined | null;
  moduleId: FacilityModuleId;
  role: string | undefined | null;
}) => isModuleEnabled(modules, moduleId) && isRoleAllowedForModule(role, moduleId);
