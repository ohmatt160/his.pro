import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { apiClient, type AuthUser } from "@/api/client";
import { refreshProfile } from "@/lib/auth-session";
import {
  authenticateStaff,
  getProfile,
} from "@/lib/facility-staff";

const IDLE_TIMEOUT_MS = 60 * 60 * 1000;
const LAST_ACTIVITY_KEY = "hispro:last-activity-at";

type LoginCredentials = {
  facilitySlug: string;
  login: string;
  password: string;
};

type AuthContextValue = {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  sessionMessage: string;
  login: (credentials: LoginCredentials) => Promise<AuthUser>;
  logout: () => void;
  logoutEverywhere: () => Promise<void>;
  clearSessionMessage: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const getLastActivityAt = () => {
  if (typeof window === "undefined") {
    return Date.now();
  }
  return Number(window.localStorage.getItem(LAST_ACTIVITY_KEY) || Date.now());
};

const markActivity = () => {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(LAST_ACTIVITY_KEY, String(Date.now()));
  }
};

const hasTimedOut = () => Date.now() - getLastActivityAt() > IDLE_TIMEOUT_MS;

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [token, setTokenState] = useState<string | null>(apiClient.getToken());
  const [user, setUserState] = useState<AuthUser | null>(apiClient.getUser());
  const [loading, setLoading] = useState(true);
  const [sessionMessage, setSessionMessage] = useState("");

  useEffect(() => {
    let isMounted = true;

    const restoreSession = async () => {
      setLoading(true);
      try {
        if ((apiClient.getUser() || apiClient.getToken()) && hasTimedOut()) {
          throw new Error("Session idle timeout");
        }

        let profile: AuthUser;
        try {
          profile = await getProfile();
        } catch {
          profile = await refreshProfile();
        }

        if (!isMounted) {
          return;
        }
        apiClient.setUser(profile);
        markActivity();
        setUserState(profile);
        setTokenState(apiClient.getToken());
        setSessionMessage("");
      } catch {
        if (!isMounted) {
          return;
        }
        const hadStoredUser = Boolean(apiClient.getUser());
        apiClient.clearToken();
        apiClient.clearUser();
        setTokenState(null);
        setUserState(null);
        if (hadStoredUser) {
          setSessionMessage("Your session expired. Please sign in again.");
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    restoreSession();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!user) {
      return;
    }

    const onActivity = () => markActivity();
    const onFocus = () => {
      if (hasTimedOut()) {
        apiClient.post("/auth/logout").catch(() => undefined);
        apiClient.clearToken();
        apiClient.clearUser();
        setTokenState(null);
        setUserState(null);
        setSessionMessage("Your session expired after being idle. Please sign in again.");
        return;
      }
      markActivity();
    };

    const events = ["click", "keydown", "mousemove", "touchstart", "scroll"];
    events.forEach((eventName) => window.addEventListener(eventName, onActivity, { passive: true }));
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onFocus);
    markActivity();

    return () => {
      events.forEach((eventName) => window.removeEventListener(eventName, onActivity));
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onFocus);
    };
  }, [user]);

  const login = async ({ facilitySlug, login, password }: LoginCredentials) => {
    setLoading(true);

    try {
      const response = await authenticateStaff({
        facilitySlug,
        login,
        password,
      });

      apiClient.setUser(response.user);
      markActivity();
      setTokenState(response.access_token);
      setUserState(response.user);
      setSessionMessage("");

      return response.user;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    apiClient.post("/auth/logout").catch(() => undefined);
    apiClient.clearToken();
    apiClient.clearUser();
    window.localStorage.removeItem(LAST_ACTIVITY_KEY);
    setTokenState(null);
    setUserState(null);
    setSessionMessage("");
  };

  const logoutEverywhere = async () => {
    await apiClient.post("/auth/logout-everywhere").catch(() => undefined);
    apiClient.clearToken();
    apiClient.clearUser();
    window.localStorage.removeItem(LAST_ACTIVITY_KEY);
    setTokenState(null);
    setUserState(null);
    setSessionMessage("You have been logged out from all sessions.");
  };

  const clearSessionMessage = () => {
    setSessionMessage("");
  };

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      sessionMessage,
      login,
      logout,
      logoutEverywhere,
      clearSessionMessage,
    }),
    [user, token, loading, sessionMessage]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }

  return context;
};
