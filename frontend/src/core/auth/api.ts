export type AuthError = {
  message: string;
};

export type Session = {
  user_id: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  locale: string;
  org_id: string;
  is_platform_admin: boolean;
};

export type AuthResult<T> = {
  data: T | null;
  error: AuthError | null;
};

type RegisterInput = {
  email: string;
  password: string;
  display_name: string;
};

type LoginInput = {
  email: string;
  password: string;
};

async function requestAuth<T>(path: string, init?: RequestInit): Promise<AuthResult<T>> {
  try {
    const response = await fetch(path, {
      ...init,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });

    const payload = (await response.json().catch(() => null)) as
      | AuthResult<T>
      | { message?: string; detail?: string }
      | null;

    if (response.ok) {
      if (payload && "data" in payload && "error" in payload) {
        return payload;
      }

      return {
        data: payload as T,
        error: null,
      };
    }

    if (payload && "error" in payload && payload.error) {
      return {
        data: null,
        error: payload.error,
      };
    }

    return {
      data: null,
      error: {
        message:
          payload && "message" in payload && typeof payload.message === "string"
            ? payload.message
            : payload && "detail" in payload && typeof payload.detail === "string"
              ? payload.detail
              : "Authentication request failed",
      },
    };
  } catch (error) {
    console.error("Authentication request failed", error);
    return {
      data: null,
      error: { message: "Authentication request failed" },
    };
  }
}

export function register(
  email: string,
  password: string,
  displayName: string,
): Promise<AuthResult<Session>> {
  const body: RegisterInput = { email, password, display_name: displayName };

  return requestAuth<Session>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function login(
  email: string,
  password: string,
): Promise<AuthResult<Session>> {
  const body: LoginInput = { email, password };

  return requestAuth<Session>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function logout(): Promise<AuthResult<null>> {
  return requestAuth<null>("/api/auth/logout", {
    method: "POST",
  });
}

export function getSession(): Promise<AuthResult<Session>> {
  return requestAuth<Session>("/api/auth/session", {
    method: "GET",
  });
}
