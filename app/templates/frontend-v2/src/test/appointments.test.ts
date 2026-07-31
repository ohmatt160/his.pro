import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "@/api/client";
import { getFacilityClinicians } from "@/lib/facility-staff";
import { loadAppointmentResources } from "@/pages/Appointments";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
  },
}));

vi.mock("@/lib/facility-staff", async () => {
  const actual = await vi.importActual<typeof import("@/lib/facility-staff")>(
    "@/lib/facility-staff"
  );

  return {
    ...actual,
    getFacilityClinicians: vi.fn(),
  };
});

describe("appointment resource loading", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("keeps patients available when clinicians, appointments, or queue fail", async () => {
    vi.mocked(apiClient.get)
      .mockResolvedValueOnce({
        patients: [
          {
            id: "patient-1",
            first_name: "Musa",
            last_name: "Bello",
            full_name: "Musa Bello",
          },
        ],
        total: 1,
      })
      .mockRejectedValueOnce(new Error("appointments unavailable"))
      .mockRejectedValueOnce(new Error("queue unavailable"));
    vi.mocked(getFacilityClinicians).mockRejectedValueOnce(
      new Error("clinicians unavailable")
    );

    const result = await loadAppointmentResources("sunrise-medical-centre");

    expect(result.patients).toHaveLength(1);
    expect(result.patients[0].full_name).toBe("Musa Bello");
    expect(result.clinicians).toEqual([]);
    expect(result.appointments).toEqual([]);
    expect(result.queue).toEqual([]);
    expect(result.errors).toEqual({
      clinicians: "Clinicians could not be loaded.",
      appointments: "Appointments could not be loaded.",
      queue: "Queue could not be loaded.",
    });
  });

  it("keeps clinicians and queue available when patients fail", async () => {
    vi.mocked(apiClient.get)
      .mockRejectedValueOnce(new Error("patients unavailable"))
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce({
        queue_entries: [
          {
            id: "queue-1",
            patient_id: "patient-1",
            department: "Front Desk",
            status: "waiting",
            queue_number: 1,
            priority: "normal",
          },
        ],
      });
    vi.mocked(getFacilityClinicians).mockResolvedValueOnce([
      {
        staffRecordId: "doctor-1",
        facilitySlug: "sunrise-medical-centre",
        fullName: "Dr. Chidi Nwosu",
        role: "doctor",
        department: "Consultations",
        email: "doctor@example.com",
        phone: "+2348000000000",
        loginId: "DOC-001",
        password: "",
        temporaryPassword: "",
        mustChangePassword: false,
        status: "active",
        createdAt: "2026-06-04T00:00:00",
      },
    ]);

    const result = await loadAppointmentResources("sunrise-medical-centre");

    expect(result.patients).toEqual([]);
    expect(result.clinicians).toHaveLength(1);
    expect(result.appointments).toEqual([]);
    expect(result.queue).toHaveLength(1);
    expect(result.errors).toEqual({
      patients: "Patients could not be loaded.",
    });
  });
});
