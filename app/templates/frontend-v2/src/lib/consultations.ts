export type ConsultationStatus = "started" | "in_progress" | "completed";

export type Consultation = {
  id: string;
  patient_id: string;
  patient_name: string;
  appointment_id?: string | null;
  appointment_status?: string | null;
  chief_complaint?: string | null;
  vital_signs: Record<string, string | number>;
  symptoms: string[];
  diagnosis: string[];
  treatment_plan?: string | null;
  prescriptions: Record<string, string>[];
  lab_orders: Record<string, string>[];
  radiology_orders: Record<string, string>[];
  follow_up_date?: string | null;
  notes?: string | null;
  status: ConsultationStatus;
  created_at: string;
  updated_at?: string | null;
};

export type ConsultationForm = {
  chief_complaint: string;
  temperature: string;
  blood_pressure: string;
  pulse: string;
  respiratory_rate: string;
  symptoms: string;
  diagnosis: string;
  treatment_plan: string;
  prescriptions: string;
  lab_orders: string;
  radiology_orders: string;
  follow_up_date: string;
  notes: string;
};

export const emptyConsultationForm: ConsultationForm = {
  chief_complaint: "",
  temperature: "",
  blood_pressure: "",
  pulse: "",
  respiratory_rate: "",
  symptoms: "",
  diagnosis: "",
  treatment_plan: "",
  prescriptions: "",
  lab_orders: "",
  radiology_orders: "",
  follow_up_date: "",
  notes: "",
};

export const toList = (value: string) =>
  value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

const ordersFromList = (value: string, key: string) =>
  toList(value).map((name) => ({ [key]: name }));

export const formFromConsultation = (consultation: Consultation): ConsultationForm => ({
  chief_complaint: consultation.chief_complaint || "",
  temperature: String(consultation.vital_signs?.temperature || ""),
  blood_pressure: String(consultation.vital_signs?.blood_pressure || ""),
  pulse: String(consultation.vital_signs?.pulse || ""),
  respiratory_rate: String(consultation.vital_signs?.respiratory_rate || ""),
  symptoms: consultation.symptoms.join(", "),
  diagnosis: consultation.diagnosis.join(", "),
  treatment_plan: consultation.treatment_plan || "",
  prescriptions: consultation.prescriptions
    .map((item) => item.medication || item.name)
    .filter(Boolean)
    .join(", "),
  lab_orders: consultation.lab_orders
    .map((item) => item.test || item.name)
    .filter(Boolean)
    .join(", "),
  radiology_orders: consultation.radiology_orders
    .map((item) => item.study || item.name)
    .filter(Boolean)
    .join(", "),
  follow_up_date: consultation.follow_up_date || "",
  notes: consultation.notes || "",
});

export const payloadFromConsultationForm = (form: ConsultationForm) => ({
  chief_complaint: form.chief_complaint.trim(),
  vital_signs: {
    temperature: form.temperature.trim(),
    blood_pressure: form.blood_pressure.trim(),
    pulse: form.pulse.trim(),
    respiratory_rate: form.respiratory_rate.trim(),
  },
  symptoms: toList(form.symptoms),
  diagnosis: toList(form.diagnosis),
  treatment_plan: form.treatment_plan.trim() || undefined,
  prescriptions: ordersFromList(form.prescriptions, "medication"),
  lab_orders: ordersFromList(form.lab_orders, "test"),
  radiology_orders: ordersFromList(form.radiology_orders, "study"),
  follow_up_date: form.follow_up_date || undefined,
  notes: form.notes.trim() || undefined,
});
