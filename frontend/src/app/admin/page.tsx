"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getUsageSummary } from "@/core/admin/api";
import type { UsageSummary } from "@/core/admin/types";
import { useI18n } from "@/core/i18n/hooks";

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export default function AdminDashboardPage() {
  const { t } = useI18n();
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getUsageSummary()
      .then(setSummary)
      .catch((err: Error) => {
        toast.error(err.message || t.admin.usageLoadFailed);
      })
      .finally(() => setLoading(false));
  }, [t.admin.usageLoadFailed]);

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-2xl font-semibold">{t.admin.dashboard}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t.admin.dashboardDescription}</p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const totalTokens =
    (summary?.total_input_tokens ?? 0) + (summary?.total_output_tokens ?? 0);

  const stats = [
    { label: t.admin.usageRecords, value: summary?.total_usage_records ?? 0 },
    { label: t.admin.totalTokens, value: totalTokens, href: "/admin/usage" },
    { label: t.admin.totalApiCalls, value: summary?.total_api_calls ?? 0, href: "/admin/usage" },
    { label: t.admin.organization, value: 0, displayValue: t.admin.platformOnly },
  ];

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold">{t.admin.dashboard}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t.admin.dashboardDescription}</p>
      </div>

      {/* Stat cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const content = (
            <Card key={stat.label} className="transition-shadow hover:shadow-md">
              <CardHeader>
                <CardDescription>{stat.label}</CardDescription>
              </CardHeader>
              <CardContent>
                  <CardTitle className="text-2xl tabular-nums">
                  {stat.displayValue ?? formatNumber(stat.value)}
                  </CardTitle>
              </CardContent>
            </Card>
          );
          return stat.href ? (
            <Link key={stat.label} href={stat.href}>
              {content}
            </Link>
          ) : (
            <div key={stat.label}>{content}</div>
          );
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t.admin.platformOverview}</CardTitle>
          <CardDescription>{t.admin.platformOverviewDescription}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-lg border p-4">
            <p className="text-sm text-muted-foreground">{t.admin.inputTokens}</p>
            <p className="mt-2 text-2xl font-semibold tabular-nums">
              {formatNumber(summary?.total_input_tokens ?? 0)}
            </p>
          </div>
          <div className="rounded-lg border p-4">
            <p className="text-sm text-muted-foreground">{t.admin.outputTokens}</p>
            <p className="mt-2 text-2xl font-semibold tabular-nums">
              {formatNumber(summary?.total_output_tokens ?? 0)}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
