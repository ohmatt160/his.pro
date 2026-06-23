import { apiClient } from "@/api/client";

export type PatientOption = {
  id: string;
  first_name: string;
  last_name: string;
  full_name?: string;
  phone?: string | null;
};

type PatientOptionEnvelope<T extends PatientOption> = {
  patients: T[];
  total: number;
};

let cached:
  | {
      scope: string;
      expiresAt: number;
      value: PatientOptionEnvelope<PatientOption>;
    }
  | undefined;
let inFlight: Promise<PatientOptionEnvelope<PatientOption>> | undefined;

const currentScope = () => {
  const user = apiClient.getUser?.();
  if (!user) {
    return null;
  }
  return [
    user.id || user.loginId,
    user.facilitySlug || "",
    user.branchId || "",
  ].join(":");
};

export const invalidatePatientOptions = () => {
  cached = undefined;
  inFlight = undefined;
};

export const getPatientOptions = async <T extends PatientOption = PatientOption>(
  limit = 200
): Promise<PatientOptionEnvelope<T>> => {
  const scope = currentScope();
  if (scope && cached?.scope === scope && cached.expiresAt > Date.now()) {
    return cached.value as PatientOptionEnvelope<T>;
  }
  if (scope && inFlight) {
    return inFlight as Promise<PatientOptionEnvelope<T>>;
  }

  const request = apiClient
    .get<PatientOption[] | PatientOptionEnvelope<PatientOption>>(
      `/patients/options?limit=${limit}`
    )
    .then((response) => {
      const value = Array.isArray(response)
        ? { patients: response, total: response.length }
        : response;
      if (scope) {
        cached = {
          scope,
          expiresAt: Date.now() + 60_000,
          value,
        };
      }
      return value;
    })
    .finally(() => {
      if (scope) {
        inFlight = undefined;
      }
    });
  if (scope) {
    inFlight = request;
  }

  return request as Promise<PatientOptionEnvelope<T>>;
};
