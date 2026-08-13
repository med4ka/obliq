"use client";

import { createContext, useContext, useCallback, useEffect, useState, type ReactNode } from "react";
import { getMe, loginApi, logoutApi, registerApi } from "@/lib/api-client";

interface User {
  id: number;
  email: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<string | null>;
  register: (email: string, password: string) => Promise<string | null>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe()
      .then((data) => {
        if (data.status === "ok" && data.user) setUser(data.user);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string): Promise<string | null> => {
    const data = await loginApi(email, password);
    if (data.status === "ok" && data.user) {
      setUser(data.user);
      return null;
    }
    return data.message ?? "Login gagal.";
  }, []);

  const register = useCallback(async (email: string, password: string): Promise<string | null> => {
    const data = await registerApi(email, password);
    if (data.status === "ok" && data.user) {
      setUser(data.user);
      return null;
    }
    return data.message ?? "Registrasi gagal.";
  }, []);

  const logout = useCallback(async () => {
    await logoutApi();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
