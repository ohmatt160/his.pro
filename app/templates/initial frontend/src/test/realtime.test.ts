import { describe, expect, it, vi } from "vitest";
import { invalidateRealtimeQueries, type RealtimeEvent } from "../lib/realtime";

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
