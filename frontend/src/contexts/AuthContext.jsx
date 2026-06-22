import { createContext, useContext, useState, useEffect } from "react";

const AuthContext = createContext(null);

const STORAGE_KEY = "alphavault_user";
const API = process.env.REACT_APP_BACKEND_URL;

const defaultUser = {
  id: null,
  email: "",
  name: "",
  avatar: "",
  hasCompletedOnboarding: false,
  preferences: {
    experience: "",
    riskTolerance: "",
    investingStyle: "",
    shariahMode: false,
    sectors: [],
    orientation: "growth",
    modelDetail: "standard",
  },
  apiKeys: {
    fmp: "",
    polygon: "",
    benzinga: "",
    openai: "",
    anthropic: "",
  },
  createdAt: null,
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (user) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [user]);

  const signup = async (email, password, name) => {
    setIsLoading(true);
    await new Promise((r) => setTimeout(r, 800));
    const newUser = {
      ...defaultUser,
      id: crypto.randomUUID(),
      email,
      name,
      createdAt: new Date().toISOString(),
    };
    setUser(newUser);
    setIsLoading(false);
    return { success: true };
  };

  const login = async (username, password) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API}/api/auth/access`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, code: password }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.success && data.token) {
        let stored = {};
        try { stored = JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; } catch { stored = {}; }
        const u = {
          ...defaultUser,
          ...stored,
          id: username,
          email: username,
          name: username,
          token: data.token,
          hasCompletedOnboarding: true,
          createdAt: stored.createdAt || new Date().toISOString(),
        };
        setUser(u);
        return { success: true };
      }
      return { success: false, message: data.message || "Invalid credentials" };
    } catch {
      return { success: false, message: "Could not reach the server" };
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
  };

  const updateUser = (updates) => {
    setUser((prev) => ({ ...prev, ...updates }));
  };

  const updatePreferences = (prefs) => {
    setUser((prev) => ({
      ...prev,
      preferences: { ...prev.preferences, ...prefs },
    }));
  };

  const updateApiKeys = (keys) => {
    setUser((prev) => ({
      ...prev,
      apiKeys: { ...prev.apiKeys, ...keys },
    }));
  };

  const completeOnboarding = (preferences) => {
    setUser((prev) => ({
      ...prev,
      hasCompletedOnboarding: true,
      preferences: { ...prev.preferences, ...preferences },
    }));
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        hasCompletedOnboarding: user?.hasCompletedOnboarding ?? false,
        isLoading,
        signup,
        login,
        logout,
        updateUser,
        updatePreferences,
        updateApiKeys,
        completeOnboarding,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
