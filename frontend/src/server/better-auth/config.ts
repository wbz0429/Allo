import { betterAuth } from "better-auth";
import Database from "better-sqlite3";
import path from "path";

const baseURL = process.env.BETTER_AUTH_URL ?? "http://localhost:2026";

// Use SQLite for local dev, PostgreSQL for production
const dbPath = path.resolve(process.cwd(), "..", "data", "auth.db");

function getDatabase() {
  if (process.env.DATABASE_URL) {
    // PostgreSQL via pg Pool
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { Pool } = require("pg") as typeof import("pg");
    return new Pool({ connectionString: process.env.DATABASE_URL });
  }
  // SQLite for local development
  return new Database(dbPath);
}

export const auth = betterAuth({
  baseURL,
  trustedOrigins: [
    baseURL,
    "http://localhost:2026",
    "http://localhost:3000",
  ],
  database: getDatabase(),
  emailAndPassword: {
    enabled: true,
  },
});

export type Session = typeof auth.$Infer.Session;
