import { describe, expect, it, vi } from "vitest";
import {
  invalidateRealtimeQueries,
  realtimeEventMatchesUserScope,
  type RealtimeEvent,
} from "../lib/realtime";

const makeQueryClient = () =>
  ({
    invalidateQueries: vi.fn(),
  } as unknown as Parameters<typeof invalidateRealtimeQueries>[0]);

describe("realtime cache invalidation", () => {
  it("ignores system events and events without a facility", () => {
    const queryClient = makeQueryClient();

    invalidateRealtimeQueries(queryClient, { type: "system.keepalive" });
    invalidateRealtimeQueries(queryClient, { type: "patient.created" });

    expect(queryClient.invalidateQueries).not.toHaveBeenCalled();
  });

  it("invalidates tenant-scoped dashboard and facility queries", () => {
    const queryClient = makeQueryClient();
    const event: RealtimeEvent = {
      type: "patient.created",
      facility_slug: "sunrise-medical-centre",
    };

    invalidateRealtimeQueries(queryClient, event);

    expect(queryClient.invalidateQueries).toHaveBeenCalledTimes(1);
    const [{ predicate }] = vi.mocked(queryClient.invalidateQueries).mock.calls[0];
    expect(predicate?.({ queryKey: ["dashboard-stats", "sunrise-medical-centre", "all"] } as never)).toBe(true);
    expect(predicate?.({ queryKey: ["dashboard-stats", "other-facility", "all"] } as never)).toBe(false);
  });

  it("invalidates workspace metadata when facility or branch settings change", () => {
    const queryClient = makeQueryClient();

    invalidateRealtimeQueries(queryClient, {
      type: "branch.modules_updated",
      facility_slug: "sunrise-medical-centre",
    });

    expect(queryClient.invalidateQueries).toHaveBeenCalledTimes(4);
  });
});

describe("realtime tenant isolation", () => {
  const user = {
    id: "user-1",
    facilitySlug: "sunrise-medical-centre",
    branchId: "branch-1",
    branchIds: ["branch-1"],
    loginId: "NUR-001",
    role: "nurse",
    fullName: "Nurse One",
  };

  it("accepts events within the signed-in facility and branch", () => {
    expect(
      realtimeEventMatchesUserScope(
        {
          type: "ward.updated",
          facility_slug: "sunrise-medical-centre",
          branch_id: "branch-1",
          roles: ["NURSE"],
        },
        user,
      ),
    ).toBe(true);
  });

  it("rejects events for another facility, branch, role, or user", () => {
    const rejectedEvents: RealtimeEvent[] = [
      { type: "patient.updated", facility_slug: "other-facility" },
      { type: "patient.updated", facility_slug: user.facilitySlug, branch_id: "branch-2" },
      { type: "patient.updated", facility_slug: user.facilitySlug, roles: ["DOCTOR"] },
      { type: "patient.updated", facility_slug: user.facilitySlug, user_id: "user-2" },
    ];

    rejectedEvents.forEach((event) => {
      expect(realtimeEventMatchesUserScope(event, user)).toBe(false);
    });
  });
});
