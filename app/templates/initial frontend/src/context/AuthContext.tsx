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
        setUserState(profile);
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

  const login = async ({ facilitySlug, login, password }: LoginCredentials) => {
    setLoading(true);

    try {
      const response = await authenticateStaff({
        facilitySlug,
        login,
        password,
      });

      apiClient.setUser(response.user);
      setTokenState(null);
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
    setTokenState(null);
    setUserState(null);
    setSessionMessage("");
  };

  const logoutEverywhere = async () => {
    await apiClient.post("/auth/logout-everywhere").catch(() => undefined);
    apiClient.clearToken();
    apiClient.clearUser();
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
