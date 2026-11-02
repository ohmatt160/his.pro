import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { useAuth } from "@/context/AuthContext";
import {
  dispatchRealtimeEvent,
  getRealtimeWebSocketUrl,
  invalidateRealtimeQueries,
  type RealtimeEvent,
} from "@/lib/realtime";

const MAX_RECONNECT_DELAY_MS = 30_000;

type RealtimeTicket = {
  ticket: string;
  expires_at: string;
};

const RealtimeBridge = () => {
  const { user, loading } = useAuth();
  const queryClient = useQueryClient();
  const reconnectTimer = useRef<number | null>(null);
  const reconnectAttempt = useRef(0);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (loading || !user?.facilitySlug) {
      return undefined;
    }

    let isActive = true;

    const clearReconnect = () => {
      if (reconnectTimer.current) {
        window.clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
    };

    const scheduleReconnect = () => {
      if (!isActive) {
        return;
      }
      const delay = Math.min(
        1000 * 2 ** reconnectAttempt.current,
        MAX_RECONNECT_DELAY_MS
      );
      reconnectAttempt.current += 1;
      reconnectTimer.current = window.setTimeout(connect, delay);
    };

    const connect = async () => {
      clearReconnect();
      const endpoint = getRealtimeWebSocketUrl();
      if (!endpoint) {
        return;
      }

      try {
        const { ticket } = await apiClient.post<RealtimeTicket>("/realtime/ticket", {});
        if (!isActive) {
          return;
        }

        const socketUrl = getRealtimeWebSocketUrl(ticket);
        if (!socketUrl) {
          return;
        }
        const socket = new WebSocket(socketUrl);
        socketRef.current = socket;

        socket.onopen = () => {
          reconnectAttempt.current = 0;
        };

        socket.onmessage = (message) => {
          try {
            const event = JSON.parse(message.data) as RealtimeEvent;
            if (event.type === "system.keepalive" || event.type === "system.connected") {
              return;
            }
            dispatchRealtimeEvent(event);
            invalidateRealtimeQueries(queryClient, event);
          } catch {
            // Ignore malformed realtime payloads; the HTTP API remains source of truth.
          }
        };

        socket.onclose = (event) => {
          if (!isActive) {
            return;
          }
          // Policy violations are authentication/origin failures. Retrying those
          // forever only creates noise and cannot repair the session.
          if (event.code === 1008) {
            return;
          }
          scheduleReconnect();
        };
      } catch {
        scheduleReconnect();
      }
    };

    connect();

    return () => {
      isActive = false;
      clearReconnect();
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [loading, queryClient, user?.facilitySlug, user?.id, user?.loginId]);

  return null;
};

export default RealtimeBridge;
