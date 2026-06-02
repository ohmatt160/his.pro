import { describe, expect, it } from "vitest";
import {
  emptyConsultationForm,
  formFromConsultation,
  payloadFromConsultationForm,
  type Consultation,
} from "../lib/consultations";

describe("consultation form payloads", () => {
  it("builds the backend consultation update payload without dropping order types", () => {
    const payload = payloadFromConsultationForm({
      ...emptyConsultationForm,
      chief_complaint: "  Fever and headache ",
      temperature: "38.1",
      blood_pressure: "120/80",
      pulse: "94",
      symptoms: "fever, headache, ",
      diagnosis: "malaria",
      treatment_plan: "Start antimalarial therapy",
      prescriptions: "Artemether, Paracetamol",
      lab_orders: "FBC, Malaria parasite",
      radiology_orders: "Chest X-ray",
      follow_up_date: "2026-06-05",
      notes: " Review in 48 hours ",
    });

    expect(payload).toMatchObject({
      chief_complaint: "Fever and headache",
      vital_signs: {
        temperature: "38.1",
        blood_pressure: "120/80",
        pulse: "94",
      },
      symptoms: ["fever", "headache"],
      diagnosis: ["malaria"],
      treatment_plan: "Start antimalarial therapy",
      prescriptions: [{ medication: "Artemether" }, { medication: "Paracetamol" }],
      lab_orders: [{ test: "FBC" }, { test: "Malaria parasite" }],
      radiology_orders: [{ study: "Chest X-ray" }],
      follow_up_date: "2026-06-05",
      notes: "Review in 48 hours",
    });
  });

  it("hydrates the editor form from an existing consultation", () => {
    const consultation: Consultation = {
      id: "record-1",
      patient_id: "patient-1",
      patient_name: "Musa Bello",
      appointment_id: "appointment-1",
      appointment_status: "IN_PROGRESS",
      chief_complaint: "Chest pain",
      vital_signs: { temperature: "37.2", blood_pressure: "130/85" },
      symptoms: ["pain", "dizziness"],
      diagnosis: ["angina"],
      treatment_plan: "Observe and review",
      prescriptions: [{ medication: "Aspirin" }],
      lab_orders: [{ test: "Troponin" }],
      radiology_orders: [{ study: "ECG" }],
      follow_up_date: "2026-06-06",
      notes: "Stable",
      status: "in_progress",
      created_at: "2026-06-02T10:00:00",
    };

    expect(formFromConsultation(consultation)).toMatchObject({
      chief_complaint: "Chest pain",
      blood_pressure: "130/85",
      symptoms: "pain, dizziness",
      diagnosis: "angina",
      prescriptions: "Aspirin",
      lab_orders: "Troponin",
      radiology_orders: "ECG",
    });
  });
});
