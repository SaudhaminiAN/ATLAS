import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  apiGet,
  apiPost,
  endpoints,
  getAccessToken,
  loadStoredTokens,
  setAuthTokens,
} from "../lib/api";
import type { AuthTokens, AuthUser, HealthStatus } from "../types/api";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  authRequired: boolean;
  registrationEnabled: boolean;
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [authRequired, setAuthRequired] = useState(false);
  const [registrationEnabled, setRegistrationEnabled] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);

  const logout = useCallback(() => {
    setAuthTokens(null);
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  const bootstrap = useCallback(async () => {
    loadStoredTokens();
    const health = await apiGet<HealthStatus>(endpoints.health());
    setAuthRequired(health.auth_enabled);
    setRegistrationEnabled(health.auth_registration_enabled);

    if (!health.auth_enabled) {
      setUser(null);
      setStatus("authenticated");
      return;
    }

    if (!getAccessToken()) {
      setStatus("unauthenticated");
      return;
    }

    try {
      const profile = await apiGet<AuthUser>(endpoints.authMe());
      setUser(profile);
      setStatus("authenticated");
    } catch {
      setAuthTokens(null);
      setUser(null);
      setStatus("unauthenticated");
    }
  }, []);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await apiPost<AuthTokens>(endpoints.authLogin(), { email, password });
    setAuthTokens(tokens);
    const profile = await apiGet<AuthUser>(endpoints.authMe());
    setUser(profile);
    setStatus("authenticated");
  }, []);

  const register = useCallback(
    async (email: string, password: string) => {
      await apiPost<AuthUser>(endpoints.authRegister(), { email, password });
      await login(email, password);
    },
    [login],
  );

  const value = useMemo(
    () => ({
      status,
      authRequired,
      registrationEnabled,
      user,
      login,
      register,
      logout,
    }),
    [status, authRequired, registrationEnabled, user, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
