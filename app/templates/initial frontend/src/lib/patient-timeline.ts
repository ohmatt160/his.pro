import { apiClient } from "@/api/client";

export type PatientTimelinePatient = {
  id: string;
  first_name: string;
  last_name: string;
  full_name?: string;
  date_of_birth: string;
  gender?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  blood_type?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  medical_history?: Record<string, unknown> | null;
  is_active: boolean;
};

export type PatientTimelineEvent = {
  id: string;
  event_type: string;
  module: string;
  title: string;
  description: string;
  status?: string | null;
  occurred_at: string;
  metadata: Record<string, unknown>;
};

export type PatientTimelineResponse = {
  patient: PatientTimelinePatient;
  events: PatientTimelineEvent[];
  total: number;
};

export const getPatientTimeline = (patientId: string) =>
  apiClient.get<PatientTimelineResponse>(`/patients/${patientId}/timeline`);

export type PatientDemographicUpdate = {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender?: string;
  phone?: string;
  email?: string;
  address?: string;
  blood_type?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
};

export const updatePatientRecord = (
  patientId: string,
  data: PatientDemographicUpdate
) => apiClient.put<PatientTimelinePatient>(`/patients/${patientId}`, data);

export const archivePatientRecord = (patientId: string) =>
  apiClient.del<{ message: string }>(`/patients/${patientId}`);

export const formatTimelineDate = (value: string) => {
  if (!value) {
    return "Unknown time";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
};

export const timelineModuleLabels: Record<string, string> = {
  reception: "Reception",
  records: "Records",
  lab: "Laboratory",
  radiology: "Radiology",
  pharmacy: "Pharmacy",
  billing: "Billing",
  nursing: "Nursing",
};

export const timelineModuleTone: Record<string, string> = {
  reception: "bg-sky-500/10 text-sky-700 border-sky-200",
  records: "bg-emerald-500/10 text-emerald-700 border-emerald-200",
  lab: "bg-cyan-500/10 text-cyan-700 border-cyan-200",
  radiology: "bg-violet-500/10 text-violet-700 border-violet-200",
  pharmacy: "bg-purple-500/10 text-purple-700 border-purple-200",
  billing: "bg-amber-500/10 text-amber-700 border-amber-200",
  nursing: "bg-rose-500/10 text-rose-700 border-rose-200",
};
