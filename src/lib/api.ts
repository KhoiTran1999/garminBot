// Client API Helper for Garmin AI Coach Pro

export interface UserProfile {
  name: string;
  email: string;
  goal?: string;
  injury?: string;
  note?: string;
  telegram_chat_id?: string;
}

export interface AnalysisResult {
  status: "success" | "warning" | "error";
  mode: string;
  report: string;
  audio_url?: string | null;
  metrics?: {
    readiness_score?: number | null;
    is_fresh?: boolean;
    fresh_msg?: string;
    date?: string;
  };
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

const TOKEN_KEY = "garmin_coach_token";
const USER_KEY = "garmin_coach_user";

export const getAuthToken = (): string | null => {
  if (typeof window === "undefined") return null;
  try {
    const local = localStorage.getItem(TOKEN_KEY);
    if (local) return local;

    // Fallback sang cookie nếu localStorage bị Safari/PWA xóa tạm thời
    const match = document.cookie.match(new RegExp("(^| )" + TOKEN_KEY + "=([^;]+)"));
    if (match) {
      const cookieVal = decodeURIComponent(match[2]);
      try {
        localStorage.setItem(TOKEN_KEY, cookieVal);
      } catch {}
      return cookieVal;
    }
  } catch (e) {
    console.warn("Lỗi đọc token:", e);
  }
  return null;
};

export const setAuthToken = (token: string): void => {
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem(TOKEN_KEY, token);
      // Lưu cookie 60 ngày để duy trì phiên qua lại giữa PWA và Safari/Chrome
      const maxAge = 60 * 24 * 60 * 60;
      document.cookie = `${TOKEN_KEY}=${encodeURIComponent(token)}; path=/; max-age=${maxAge}; SameSite=Lax`;
    } catch (e) {
      console.warn("Lỗi lưu token:", e);
    }
  }
};

export const clearAuthToken = (): void => {
  if (typeof window !== "undefined") {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      document.cookie = `${TOKEN_KEY}=; path=/; max-age=0; SameSite=Lax`;
    } catch (e) {
      console.warn("Lỗi xóa token:", e);
    }
  }
};

export const getStoredUser = (): UserProfile | null => {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

export const setStoredUser = (user: UserProfile): void => {
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } catch (e) {
      console.warn("Lỗi lưu user cache:", e);
    }
  }
};

async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    clearAuthToken();
    if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
      window.location.href = "/login";
    }
    const err = new Error("Phiên làm việc hết hạn. Vui lòng đăng nhập lại.");
    (err as any).status = 401;
    throw err;
  }

  // Đọc response text một lần duy nhất để tránh lỗi "body stream already read"
  const rawText = await response.text();
  let data: any = null;
  try {
    data = rawText ? JSON.parse(rawText) : null;
  } catch {
    // rawText không phải JSON (ví dụ Vercel HTML error page 500/404)
  }

  if (!response.ok) {
    let errorDetail = `Lỗi máy chủ (${response.status})`;
    if (data && data.detail) {
      errorDetail = data.detail;
    } else if (rawText && !rawText.trim().startsWith("<")) {
      errorDetail = rawText.length > 200 ? rawText.substring(0, 200) + "..." : rawText;
    } else if (response.status === 500) {
      errorDetail = "Lỗi máy chủ nội bộ (500). Vui lòng kiểm tra lại cấu hình biến môi trường trên Vercel.";
    } else if (response.status === 404) {
      errorDetail = `Không tìm thấy endpoint API (${url}).`;
    }
    throw new Error(errorDetail);
  }

  if (data === null) {
    throw new Error("Phản hồi từ máy chủ không đúng định dạng JSON.");
  }

  return data;
}

export const api = {
  async login(email: string, password: string): Promise<{ token: string; user: UserProfile }> {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const rawText = await res.text();
    let data: any = null;
    try {
      data = rawText ? JSON.parse(rawText) : null;
    } catch {
      // Body không phải JSON
    }

    if (!res.ok) {
      let errorMsg = data?.detail;
      if (!errorMsg) {
        if (res.status === 500) {
          errorMsg = "Lỗi máy chủ nội bộ (500). Backend API gặp sự cố khởi động trên Vercel.";
        } else if (res.status === 404) {
          errorMsg = "Không tìm thấy API đăng nhập (404).";
        } else {
          errorMsg = `Đăng nhập thất bại (Mã lỗi ${res.status})`;
        }
      }
      throw new Error(errorMsg);
    }

    if (!data || !data.token) {
      throw new Error("Phản hồi đăng nhập không hợp lệ.");
    }

    setAuthToken(data.token);
    if (data.user) {
      setStoredUser(data.user);
    }
    return data;
  },

  async getMe(): Promise<{ user: UserProfile }> {
    return fetchWithAuth("/api/auth/me");
  },

  async getOverview(): Promise<any> {
    return fetchWithAuth("/api/overview");
  },

  async getGarminStatus(): Promise<{ is_fresh: boolean; message: string }> {
    return fetchWithAuth("/api/garmin/status");
  },

  async runAnalysis(mode: string, userNote?: string): Promise<AnalysisResult> {
    return fetchWithAuth("/api/analysis/run", {
      method: "POST",
      body: JSON.stringify({ mode, user_note: userNote || null }),
    });
  },

  async sendChatMessage(question: string): Promise<{ reply: string }> {
    return fetchWithAuth("/api/chat", {
      method: "POST",
      body: JSON.stringify({ question }),
    });
  },

  async getChatHistory(): Promise<{ history: ChatMessage[] }> {
    return fetchWithAuth("/api/chat/history");
  },

  async updateProfile(data: { goal?: string; injury?: string; note?: string }): Promise<{ status: string; message: string }> {
    return fetchWithAuth("/api/profile/update", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
};
