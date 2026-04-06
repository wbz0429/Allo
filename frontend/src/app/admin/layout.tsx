"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Toaster, toast } from "sonner";

import { getSession } from "@/core/auth/api";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

export default function AdminLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const pathname = usePathname();
  const router = useRouter();
  const { t } = useI18n();
  const [queryClient] = useState(() => new QueryClient());
  const [authorized, setAuthorized] = useState(false);

  const navItems = [
    { href: "/admin", label: t.admin.dashboard },
    { href: "/admin/organizations", label: t.admin.organizations },
    { href: "/admin/usage", label: t.admin.usage },
  ];

  useEffect(() => {
    void getSession().then((res) => {
        if (!res.data?.user_id) {
          if (res.error) {
            toast.error(res.error.message ?? "Failed to verify session");
        }

        router.replace("/login?callbackUrl=" + encodeURIComponent(pathname));
        return;
      }

      setAuthorized(true);
    });
  }, [pathname, router]);

  if (!authorized) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">{t.admin.checkingAccess}</p>
      </div>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex min-h-screen flex-col">
        {/* Top nav */}
        <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-6">
            <Link href="/admin" className="text-sm font-semibold">
              {t.admin.platformAdmin}
            </Link>
            <nav className="flex items-center gap-1">
              {navItems.map((item) => {
                const isActive =
                  item.href === "/admin"
                    ? pathname === "/admin"
                    : pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "rounded-md px-3 py-1.5 text-sm transition-colors",
                      isActive
                        ? "bg-accent font-medium text-accent-foreground"
                        : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                    )}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
            <div className="ml-auto">
              <Link
                href="/workspace"
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                {t.admin.backToWorkspace}
              </Link>
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-8">
          {children}
        </main>
      </div>
      <Toaster position="top-center" />
    </QueryClientProvider>
  );
}
