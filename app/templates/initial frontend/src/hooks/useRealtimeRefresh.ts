import { useEffect, useRef } from "react";
import { HISPRO_REALTIME_EVENT, type RealtimeEvent } from "@/lib/realtime";

type RealtimeRefreshOptions = {
  eventTypes: string[];
  onRefresh: () => void | Promise<void>;
  enabled?: boolean;
  debounceMs?: number;
};

const matchesEventType = (eventType: string, patterns: string[]) =>
  patterns.some((pattern) =>
    pattern.endsWith("*")
      ? eventType.startsWith(pattern.slice(0, -1))
      : eventType === pattern
  );

export const useRealtimeRefresh = ({
  eventTypes,
  onRefresh,
  enabled = true,
  debounceMs = 400,
}: RealtimeRefreshOptions) => {
  const refreshRef = useRef(onRefresh);
  const eventTypesRef = useRef(eventTypes);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    refreshRef.current = onRefresh;
  }, [onRefresh]);

  useEffect(() => {
    eventTypesRef.current = eventTypes;
  }, [eventTypes]);

  useEffect(() => {
    if (!enabled) {
      return undefined;
    }

    const clearTimer = () => {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };

    const handleRealtimeEvent = (event: Event) => {
      const realtimeEvent = (event as CustomEvent<RealtimeEvent>).detail;
      if (!realtimeEvent?.type || !matchesEventType(realtimeEvent.type, eventTypesRef.current)) {
        return;
      }

      clearTimer();
      timerRef.current = window.setTimeout(() => {
        refreshRef.current();
      }, debounceMs);
    };

    window.addEventListener(HISPRO_REALTIME_EVENT, handleRealtimeEvent);
    return () => {
      clearTimer();
      window.removeEventListener(HISPRO_REALTIME_EVENT, handleRealtimeEvent);
    };
  }, [debounceMs, enabled]);
};
