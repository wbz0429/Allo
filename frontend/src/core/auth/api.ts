export type AuthError = {
  message: string;
};

export type Session = {
  session: {
    token?: string;
    userId?: string;
    expiresAt?: string;
  };
  user: {
    id: string;
    email: string;
    name?: string;
    displayName?: string;
  };
};

export type AuthResult<T> = {
  data: T | null;
  error: AuthError | null;
};

type RegisterInput = {
  email: string;
  password: string;
  displayName: string;
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
      | { message?: string }
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
  const body: RegisterInput = { email, password, displayName };

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
