import { describe, expect, it } from "vitest";
import { emptyObservationForm, observationPayload } from "../lib/wards";

describe("ward observation payload", () => {
  it("builds a nursing observation request with vitals and notes", () => {
    expect(
      observationPayload({
        ...emptyObservationForm,
        temperature: " 37.8 ",
        blood_pressure: "118/76",
        pulse: "84",
        respiratory_rate: "18",
        note: " Patient stable after medication ",
        medication_round: "Paracetamol administered",
      })
    ).toMatchObject({
      vital_signs: {
        temperature: "37.8",
        blood_pressure: "118/76",
        pulse: "84",
        respiratory_rate: "18",
      },
      note: "Patient stable after medication",
      medication_round: "Paracetamol administered",
    });
  });
});
