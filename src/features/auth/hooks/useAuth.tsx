import type { ReactNode } from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { authRepo } from "../../../shared/api/authRepo";
import { clearToken, getToken, setToken } from "../../../shared/auth/tokenStore";
import type { RoleMode } from "../../../shared/types/role";

type AuthUser = {
  userId: string;
  username: string;
  displayName?: string | null;
  role: RoleMode;
};

type AuthContextValue = {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  register: (
    username: string,
    pin: string,
    displayName?: string,
    role?: RoleMode
  ) => Promise<AuthUser | null>;
  login: (username: string, pin: string) => Promise<AuthUser | null>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setTokenState] = useState<string | null>(getToken());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    authRepo
      .me()
      .then((data) => {
        setUser(data);
      })
      .catch((error: { status?: number; message?: string }) => {
        if (error?.status === 401) {
          console.warn("Auth expired; redirecting to login");
          clearToken();
          setTokenState(null);
          setUser(null);
          return;
        }
        console.warn("Auth check failed", error);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, [token]);

  const login = useCallback(async (username: string, pin: string) => {
    try {
      const result = await authRepo.login({ username, pin });
      setToken(result.token);
      setTokenState(result.token);
      const profile = await authRepo.me();
      setUser(profile);
      return profile;
    } catch {
      return null;
    }
  }, []);

  const register = useCallback(
    async (
      username: string,
      pin: string,
      displayName?: string,
      role?: RoleMode
    ) => {
      try {
        const result = await authRepo.register({
          username,
          pin,
          displayName,
          role: role ?? "PLAYER",
        });
        setToken(result.token);
        setTokenState(result.token);
        const profile = await authRepo.me();
        setUser(profile);
        return profile;
      } catch {
        return null;
      }
    },
    []
  );

  const logout = useCallback(() => {
    clearToken();
    setTokenState(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, token, loading, login, register, logout }),
    [user, token, loading, login, register, logout]
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
