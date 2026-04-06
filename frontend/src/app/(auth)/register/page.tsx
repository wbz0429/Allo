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
import { register } from "@/core/auth/api";
import { useI18n } from "@/core/i18n/hooks";

export default function RegisterPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const result = await register(email, password, name);

      if (result.error) {
        setError(result.error.message ?? t.auth.register.failed);
        return;
      }

      router.push("/workspace");
    } catch {
      setError(t.auth.register.unexpectedError);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle className="text-2xl">{t.auth.register.title}</CardTitle>
        <CardDescription>
          {t.auth.register.description}
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="flex flex-col gap-4">
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
          <div className="flex flex-col gap-2">
            <label htmlFor="name" className="text-sm font-medium">
              {t.auth.register.name}
            </label>
            <Input
              id="name"
              type="text"
              placeholder={t.auth.register.namePlaceholder}
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              autoComplete="name"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="email" className="text-sm font-medium">
              {t.auth.register.email}
            </label>
            <Input
              id="email"
              type="email"
              placeholder={t.auth.register.emailPlaceholder}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label htmlFor="password" className="text-sm font-medium">
              {t.auth.register.password}
            </label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>
        </CardContent>
        <CardFooter className="flex flex-col gap-3">
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? t.auth.register.submitting : t.auth.register.submit}
          </Button>
          <p className="text-sm text-muted-foreground">
            {t.auth.register.hasAccount}{" "}
            <Link href="/login" className="text-primary underline underline-offset-2 hover:no-underline">
              {t.auth.register.signIn}
            </Link>
          </p>
        </CardFooter>
      </form>
    </Card>
  );
}
