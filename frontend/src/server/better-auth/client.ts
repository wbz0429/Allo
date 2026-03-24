import type { AuthClientResult, Session } from "./types";

type EmailSignUpInput = {
  email: string;
  password: string;
  name: string;
};

type EmailSignInInput = {
  email: string;
  password: string;
};

async function requestAuth(path: string, init?: RequestInit): Promise<AuthClientResult> {
  const response = await fetch(path, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  const payload = (await response.json()) as AuthClientResult;
  if (!response.ok && !payload.error) {
    return { data: null, error: { message: "Authentication request failed" } };
  }
  return payload;
}

export const authClient = {
  signUp: {
    email(input: EmailSignUpInput): Promise<AuthClientResult> {
      return requestAuth("/api/auth/sign-up/email", {
        method: "POST",
        body: JSON.stringify(input),
      });
    },
  },
  signIn: {
    email(input: EmailSignInInput): Promise<AuthClientResult> {
      return requestAuth("/api/auth/sign-in/email", {
        method: "POST",
        body: JSON.stringify(input),
      });
    },
  },
  getSession(): Promise<AuthClientResult> {
    return requestAuth("/api/auth/session", { method: "GET" });
  },
  async signOut(): Promise<void> {
    await requestAuth("/api/auth/sign-out", { method: "POST" });
  },
};

export type { Session };
