import { randomBytes, scryptSync, timingSafeEqual } from "crypto";
import { mkdir, readFile, writeFile } from "fs/promises";
import path from "path";

import { cookies } from "next/headers";

const SESSION_COOKIE_NAME = "better-auth.session_token";
const DEV_AUTH_DATA_DIR = path.resolve(process.cwd(), "..", "data");
const USERS_FILE = path.join(DEV_AUTH_DATA_DIR, "local-dev-auth-users.json");
const SESSIONS_FILE = path.join(DEV_AUTH_DATA_DIR, "local-dev-auth-sessions.json");
const SESSION_TTL_MS = 1000 * 60 * 60 * 24 * 7;

type LocalDevUserRecord = {
  id: string;
  email: string;
  name: string;
  passwordHash: string;
  createdAt: string;
};

type LocalDevSessionRecord = {
  token: string;
  userId: string;
  expiresAt: string;
  createdAt: string;
};

type LocalDevUsersStore = {
  users: LocalDevUserRecord[];
};

type LocalDevSessionsStore = {
  sessions: LocalDevSessionRecord[];
};

export type LocalDevSession = {
  session: {
    token: string;
    userId: string;
    expiresAt: string;
  };
  user: {
    id: string;
    email: string;
    name: string;
  };
};

export type LocalDevAuthResult = {
  data: LocalDevSession | null;
  error: { message: string } | null;
};

function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

function generateId(prefix: string): string {
  return `${prefix}_${randomBytes(12).toString("hex")}`;
}

function hashPassword(password: string): string {
  const salt = randomBytes(16).toString("hex");
  const hash = scryptSync(password, salt, 64).toString("hex");
  return `${salt}:${hash}`;
}

function verifyPassword(password: string, storedHash: string): boolean {
  const [salt, expectedHash] = storedHash.split(":");
  if (!salt || !expectedHash) {
    return false;
  }

  const actualHash = scryptSync(password, salt, 64);
  const expectedBuffer = Buffer.from(expectedHash, "hex");
  if (actualHash.length !== expectedBuffer.length) {
    return false;
  }

  return timingSafeEqual(actualHash, expectedBuffer);
}

async function ensureDataDir(): Promise<void> {
  await mkdir(DEV_AUTH_DATA_DIR, { recursive: true });
}

async function readStore<T>(filePath: string, fallback: T): Promise<T> {
  try {
    const raw = await readFile(filePath, "utf-8");
    return JSON.parse(raw) as T;
  } catch (error) {
    if (
      error instanceof Error &&
      "code" in error &&
      error.code === "ENOENT"
    ) {
      return fallback;
    }
    throw error;
  }
}

async function writeStore(filePath: string, value: unknown): Promise<void> {
  await ensureDataDir();
  await writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf-8");
}

async function readUsers(): Promise<LocalDevUsersStore> {
  return readStore(USERS_FILE, { users: [] satisfies LocalDevUserRecord[] });
}

async function writeUsers(store: LocalDevUsersStore): Promise<void> {
  await writeStore(USERS_FILE, store);
}

async function readSessions(): Promise<LocalDevSessionsStore> {
  return readStore(SESSIONS_FILE, { sessions: [] satisfies LocalDevSessionRecord[] });
}

async function writeSessions(store: LocalDevSessionsStore): Promise<void> {
  await writeStore(SESSIONS_FILE, store);
}

function pruneExpiredSessions(store: LocalDevSessionsStore): LocalDevSessionsStore {
  const now = Date.now();
  return {
    sessions: store.sessions.filter((session) => {
      const expiresAt = Date.parse(session.expiresAt);
      return Number.isFinite(expiresAt) && expiresAt > now;
    }),
  };
}

function buildSession(user: LocalDevUserRecord, session: LocalDevSessionRecord): LocalDevSession {
  return {
    session: {
      token: session.token,
      userId: session.userId,
      expiresAt: session.expiresAt,
    },
    user: {
      id: user.id,
      email: user.email,
      name: user.name,
    },
  };
}

async function persistSession(user: LocalDevUserRecord): Promise<LocalDevSession> {
  const sessionsStore = pruneExpiredSessions(await readSessions());
  const now = new Date();
  const session: LocalDevSessionRecord = {
    token: generateId("dev_session"),
    userId: user.id,
    createdAt: now.toISOString(),
    expiresAt: new Date(now.getTime() + SESSION_TTL_MS).toISOString(),
  };

  sessionsStore.sessions = sessionsStore.sessions.filter(
    (existingSession) => existingSession.userId !== user.id,
  );
  sessionsStore.sessions.push(session);
  await writeSessions(sessionsStore);

  return buildSession(user, session);
}

export async function signUpWithLocalDevAuth(input: {
  email: string;
  password: string;
  name: string;
}): Promise<LocalDevAuthResult> {
  const email = normalizeEmail(input.email);
  const name = input.name.trim();
  const password = input.password;

  if (!name) {
    return { data: null, error: { message: "Name is required" } };
  }
  if (!email) {
    return { data: null, error: { message: "Email is required" } };
  }
  if (password.length < 8) {
    return { data: null, error: { message: "Password must be at least 8 characters" } };
  }

  const usersStore = await readUsers();
  const existingUser = usersStore.users.find((user) => user.email === email);
  if (existingUser) {
    return { data: null, error: { message: "An account with this email already exists" } };
  }

  const user: LocalDevUserRecord = {
    id: generateId("dev_user"),
    email,
    name,
    passwordHash: hashPassword(password),
    createdAt: new Date().toISOString(),
  };
  usersStore.users.push(user);
  await writeUsers(usersStore);

  return { data: await persistSession(user), error: null };
}

export async function signInWithLocalDevAuth(input: {
  email: string;
  password: string;
}): Promise<LocalDevAuthResult> {
  const email = normalizeEmail(input.email);
  const usersStore = await readUsers();
  const user = usersStore.users.find((candidate) => candidate.email === email);

  if (!user || !verifyPassword(input.password, user.passwordHash)) {
    return { data: null, error: { message: "Invalid email or password" } };
  }

  return { data: await persistSession(user), error: null };
}

export async function getLocalDevSessionByToken(token: string | undefined): Promise<LocalDevSession | null> {
  if (!token) {
    return null;
  }

  const sessionsStore = pruneExpiredSessions(await readSessions());
  await writeSessions(sessionsStore);
  const session = sessionsStore.sessions.find((candidate) => candidate.token === token);
  if (!session) {
    return null;
  }

  const usersStore = await readUsers();
  const user = usersStore.users.find((candidate) => candidate.id === session.userId);
  if (!user) {
    return null;
  }

  return buildSession(user, session);
}

export async function getLocalDevSessionFromCookies(): Promise<LocalDevSession | null> {
  const cookieStore = await cookies();
  return getLocalDevSessionByToken(cookieStore.get(SESSION_COOKIE_NAME)?.value);
}

export async function signOutLocalDevSession(token: string | undefined): Promise<void> {
  if (!token) {
    return;
  }

  const sessionsStore = await readSessions();
  const nextStore = {
    sessions: sessionsStore.sessions.filter((session) => session.token !== token),
  };
  await writeSessions(nextStore);
}

export function getLocalDevSessionCookieName(): string {
  return SESSION_COOKIE_NAME;
}
