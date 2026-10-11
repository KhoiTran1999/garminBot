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

export const getAuthToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
};

export const setAuthToken = (token: string): void => {
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, token);
  }
};

export const clearAuthToken = (): void => {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
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
    throw new Error("Phiên làm việc hết hạn. Vui lòng đăng nhập lại.");
  }

  if (!response.ok) {
    let errorDetail = `Lỗi máy chủ (${response.status})`;
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail || errorDetail;
    } catch {
      const errorText = await response.text();
      if (errorText) {
        errorDetail = errorText.length > 200 ? errorText.substring(0, 200) + "..." : errorText;
      }
    }
    throw new Error(errorDetail);
  }

  try {
    return await response.json();
  } catch {
    throw new Error("Phản hồi từ máy chủ không đúng định dạng JSON.");
  }
}

export const api = {
  async login(email: string, password: string): Promise<{ token: string; user: UserProfile }> {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Đăng nhập thất bại");
    }
    setAuthToken(data.token);
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
