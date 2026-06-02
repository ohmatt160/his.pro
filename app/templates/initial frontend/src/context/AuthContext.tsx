import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { apiClient, type AuthUser } from "@/api/client";
import {
  authenticateStaff,
  getProfile,
  type StaffRole,
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
  login: (credentials: LoginCredentials) => Promise<AuthUser>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [token, setTokenState] = useState<string | null>(apiClient.getToken());
  const [user, setUserState] = useState<AuthUser | null>(apiClient.getUser());
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getProfile()
      .then((profile) => {
        apiClient.setUser(profile);
        setUserState(profile);
      })
      .catch(() => {
        apiClient.clearToken();
        apiClient.clearUser();
        setTokenState(null);
        setUserState(null);
      })
      .finally(() => setLoading(false));
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
  };

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      login,
      logout,
    }),
    [user, token, loading]
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
