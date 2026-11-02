import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { apiClient } from "@/api/client";
import {
  dispatchRealtimeEvent,
  getRealtimeWebSocketUrl,
  invalidateRealtimeQueries,
  realtimeEventMatchesUserScope,
  type RealtimeEvent,
} from "@/lib/realtime";

const MAX_RECONNECT_DELAY_MS = 30_000;

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
      if (!isActive || reconnectTimer.current) return;
      const delay = Math.min(1000 * 2 ** reconnectAttempt.current, MAX_RECONNECT_DELAY_MS);
      reconnectAttempt.current += 1;
      reconnectTimer.current = window.setTimeout(() => {
        reconnectTimer.current = null;
        void connect();
      }, delay);
    };

    async function connect() {
      clearReconnect();
      const socketUrl = getRealtimeWebSocketUrl();
      if (!socketUrl) return;

      let ticket: string;
      try {
        const response = await apiClient.post<{ ticket: string }>("/realtime/ticket", {});
        ticket = response.ticket;
      } catch {
        scheduleReconnect();
        return;
      }
      if (!isActive) return;

      const url = new URL(socketUrl);
      url.searchParams.set("ticket", ticket);
      const socket = new WebSocket(url.toString());
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
          if (!realtimeEventMatchesUserScope(event, user)) {
            return;
          }
          dispatchRealtimeEvent(event);
          invalidateRealtimeQueries(queryClient, event);
        } catch {
          // Ignore malformed realtime payloads; the HTTP API remains source of truth.
        }
      };

      socket.onclose = () => {
        scheduleReconnect();
      };
    }

    connect();

    return () => {
      isActive = false;
      clearReconnect();
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [loading, queryClient, user]);

  return null;
};

export default RealtimeBridge;
