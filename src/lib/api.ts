// Client API Helper for Garmin AI Coach Pro

export interface UserProfile {
  name: string;
  email: string;
  goal?: string;
  injury?: string;
  note?: string;
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
    if (response.status === 504 || (rawText && rawText.includes("FUNCTION_INVOCATION_TIMEOUT"))) {
      errorDetail = "Yêu cầu phản hồi quá thời gian quy định của máy chủ Vercel (Timeout). AI cần thêm thời gian xử lý dữ liệu Garmin, bạn vui lòng gửi lại hoặc hỏi câu hỏi ngắn hơn một chút nhé!";
    } else if (data && data.detail) {
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

  async sendChatMessageStream(
    question: string,
    onStatus?: (status: string) => void,
    onChunk?: (chunk: string) => void,
    onDone?: (reply: string) => void,
    onError?: (error: string) => void
  ): Promise<string> {
    const token = getAuthToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "Accept": "text/event-stream",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch("/api/chat", {
      method: "POST",
      headers,
      body: JSON.stringify({ question, stream: true }),
    });

    if (response.status === 401) {
      clearAuthToken();
      if (typeof window !== "undefined" && !window.location.pathname.includes("/login")) {
        window.location.href = "/login";
      }
      throw new Error("Phiên làm việc hết hạn. Vui lòng đăng nhập lại.");
    }

    if (!response.ok) {
      const rawText = await response.text();
      let errorMsg = `Lỗi máy chủ (${response.status})`;
      if (response.status === 504 || rawText.includes("FUNCTION_INVOCATION_TIMEOUT")) {
        errorMsg = "Yêu cầu phản hồi quá thời gian quy định của máy chủ Vercel (Timeout). AI cần thêm thời gian xử lý dữ liệu Garmin, bạn vui lòng gửi lại câu hỏi nhé!";
      } else {
        try {
          const parsed = JSON.parse(rawText);
          if (parsed.detail) errorMsg = parsed.detail;
        } catch {
          if (rawText && !rawText.trim().startsWith("<")) errorMsg = rawText;
        }
      }
      if (onError) onError(errorMsg);
      throw new Error(errorMsg);
    }

    if (!response.body) {
      throw new Error("Trình duyệt không hỗ trợ đọc luồng dữ liệu (ReadableStream).");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let accumulatedText = "";
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          const lines = part.split("\n");
          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith("data:")) {
              const dataStr = trimmed.replace(/^data:\s*/, "").trim();
              if (!dataStr) continue;
              try {
                const parsed = JSON.parse(dataStr);
                if (parsed.type === "status") {
                  if (onStatus) onStatus(parsed.message);
                } else if (parsed.type === "chunk") {
                  accumulatedText += parsed.text;
                  if (onChunk) onChunk(parsed.text);
                } else if (parsed.type === "done") {
                  if (onDone) onDone(parsed.reply || accumulatedText);
                } else if (parsed.type === "error") {
                  if (onError) onError(parsed.message);
                  throw new Error(parsed.message);
                }
              } catch (parseErr) {
                console.warn("Lỗi phân tích cú pháp SSE:", parseErr, dataStr);
              }
            }
          }
        }
      }
    } catch (streamErr: any) {
      if (onError) onError(streamErr.message);
      throw streamErr;
    }

    return accumulatedText;
  },

  async sendChatMessage(question: string): Promise<{ reply: string }> {
    return fetchWithAuth("/api/chat", {
      method: "POST",
      body: JSON.stringify({ question, stream: false }),
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
