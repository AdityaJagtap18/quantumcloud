import { createContext, useContext, useState, type ReactNode } from "react";
import { authApi } from "../api/endpoints";

interface AuthContextValue {
  token: string | null;
  email: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("qc_token"));
  const [email, setEmail] = useState<string | null>(() => localStorage.getItem("qc_email"));

  async function login(emailInput: string, password: string) {
    const resp = await authApi.login(emailInput, password);
    localStorage.setItem("qc_token", resp.data.access_token);
    localStorage.setItem("qc_email", emailInput);
    setToken(resp.data.access_token);
    setEmail(emailInput);
  }

  async function register(emailInput: string, password: string) {
    await authApi.register(emailInput, password);
    await login(emailInput, password);
  }

  function logout() {
    localStorage.removeItem("qc_token");
    localStorage.removeItem("qc_email");
    setToken(null);
    setEmail(null);
  }

  return (
    <AuthContext.Provider value={{ token, email, isAuthenticated: !!token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
