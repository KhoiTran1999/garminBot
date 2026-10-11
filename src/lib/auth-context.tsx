"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { 
  api, 
  UserProfile, 
  getAuthToken, 
  clearAuthToken, 
  getStoredUser, 
  setStoredUser 
} from "./api";

interface AuthContextType {
  user: UserProfile | null;
  loading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: false,
  login: async () => {},
  logout: () => {},
  refreshProfile: async () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Khởi tạo ngay lập tức từ bộ nhớ cache cục bộ để tránh bị chớp giật hoặc đòi login lại
  const [user, setUser] = useState<UserProfile | null>(() => getStoredUser());
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  const loadUser = async () => {
    const token = getAuthToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      if (pathname !== "/login") {
        router.push("/login");
      }
      return;
    }

    // Nếu đã có thông tin user lưu từ trước, hiển thị ngay không để trống
    const cachedUser = getStoredUser();
    if (cachedUser && !user) {
      setUser(cachedUser);
    }

    try {
      const res = await api.getMe();
      if (res && res.user) {
        setUser(res.user);
        setStoredUser(res.user);
      }
    } catch (err: any) {
      console.warn("Kiểm tra xác thực:", err);
      // CHỈ xóa token và chuyển hướng về /login nếu backend trả về đúng mã 401 (hết hạn / sai token)
      if (err?.status === 401 || err?.message?.includes("Phiên làm việc hết hạn") || err?.message?.includes("401")) {
        clearAuthToken();
        setUser(null);
        if (pathname !== "/login") {
          router.push("/login");
        }
      }
      // Nếu do mạng chập chờn, server cold start hoặc Notion lag: giữ nguyên tài khoản đã đăng nhập!
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUser();
  }, [pathname]);

  const login = async (email: string, pass: string) => {
    const res = await api.login(email, pass);
    setUser(res.user);
    setStoredUser(res.user);
    router.push("/");
  };

  const logout = () => {
    clearAuthToken();
    setUser(null);
    router.push("/login");
  };

  const refreshProfile = async () => {
    try {
      const res = await api.getMe();
      if (res && res.user) {
        setUser(res.user);
        setStoredUser(res.user);
      }
    } catch (err) {
      console.error("Refresh profile failed:", err);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
