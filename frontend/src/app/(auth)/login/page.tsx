"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { login } from "@/core/auth/api";
import { useI18n } from "@/core/i18n/hooks";

export default function LoginPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const isDev = process.env.NODE_ENV !== "production";

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const result = await login(email, password);

      if (result.error) {
        setError(result.error.message ?? t.auth.login.failed);
        return;
      }

      router.push("/workspace");
    } catch {
      setError(t.auth.login.unexpectedError);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle className="text-2xl">{t.auth.login.title}</CardTitle>
        <CardDescription>
          {t.auth.login.description}
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="flex flex-col gap-4">
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
          {isDev && (
            <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm">
              <p className="font-medium text-amber-200">{t.auth.login.devAccount}</p>
              <p className="mt-1 text-amber-100/90">Email: <code>dev@allo.local</code></p>
              <p className="text-amber-100/90">Password: <code>Password123!</code></p>
              <Button
                type="button"
                variant="outline"
                className="mt-3 w-full"
                onClick={() => {
                  setEmail("dev@allo.local");
                  setPassword("Password123!");
                  setError(null);
                }}
              >
                {t.auth.login.fillDevAccount}
              </Button>
            </div>
          )}
          <div className="flex flex-col gap-2">
            <label htmlFor="email" className="text-sm font-medium">
              {t.auth.login.email}
            </label>
            <Input
              id="email"
              type="email"
              placeholder={t.auth.login.emailPlaceholder}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="password" className="text-sm font-medium">
              {t.auth.login.password}
            </label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>
        </CardContent>
        <CardFooter className="flex flex-col gap-3">
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? t.auth.login.submitting : t.auth.login.submit}
          </Button>
          <p className="text-sm text-muted-foreground">
            {t.auth.login.noAccount}{" "}
            <Link href="/register" className="text-primary underline underline-offset-2 hover:no-underline">
              {t.auth.login.register}
            </Link>
          </p>
        </CardFooter>
      </form>
    </Card>
  );
}
