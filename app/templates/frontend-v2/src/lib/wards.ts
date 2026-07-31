export type WardBed = {
  id: string;
  facility_slug: string;
  ward_name: string;
  bed_number: string;
  status: "AVAILABLE" | "OCCUPIED" | "MAINTENANCE";
  notes?: string | null;
};

export type WardAdmission = {
  id: string;
  facility_slug: string;
  patient_id: string;
  patient_name: string;
  patient_phone?: string | null;
  bed_id?: string | null;
  bed_number?: string | null;
  ward_name: string;
  reason?: string | null;
  acuity: "normal" | "urgent";
  status: "ACTIVE" | "DISCHARGED" | "TRANSFERRED";
  observations: Record<string, unknown>[];
  nursing_notes: Record<string, unknown>[];
  admitted_at: string;
  discharged_at?: string | null;
};

export type WardObservationForm = {
  temperature: string;
  blood_pressure: string;
  pulse: string;
  respiratory_rate: string;
  note: string;
  medication_round: string;
};

export const emptyObservationForm: WardObservationForm = {
  temperature: "",
  blood_pressure: "",
  pulse: "",
  respiratory_rate: "",
  note: "",
  medication_round: "",
};

export const observationPayload = (form: WardObservationForm) => ({
  vital_signs: {
    temperature: form.temperature.trim(),
    blood_pressure: form.blood_pressure.trim(),
    pulse: form.pulse.trim(),
    respiratory_rate: form.respiratory_rate.trim(),
  },
  note: form.note.trim() || undefined,
  medication_round: form.medication_round.trim() || undefined,
});
