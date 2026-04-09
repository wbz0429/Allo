"use client";

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
import { getUsageSummary, getUserUsageRanking } from "@/core/admin/api";
import type { UsageSummary, UserUsageRanking } from "@/core/admin/types";
import { useI18n } from "@/core/i18n/hooks";

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export default function AdminUsagePage() {
  const { t } = useI18n();
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [ranking, setRanking] = useState<UserUsageRanking | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getUsageSummary(), getUserUsageRanking()])
      .then(([s, u]) => {
        setSummary(s);
        setRanking(u);
      })
      .catch((err: Error) => {
        toast.error(err.message || t.admin.usageLoadFailed);
      })
      .finally(() => setLoading(false));
  }, [t.admin.usageLoadFailed]);

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-2xl font-semibold">{t.admin.usage}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t.admin.usageDescription}</p>
        <div className="grid gap-4 sm:grid-cols-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-32" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-40 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const items = ranking?.items ?? [];

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold">{t.admin.usage}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {t.admin.usageDescription}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardDescription>{t.admin.totalTokens}</CardDescription>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-2xl tabular-nums">
              {formatNumber(
                (summary?.total_input_tokens ?? 0) +
                  (summary?.total_output_tokens ?? 0),
              )}
            </CardTitle>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>{t.admin.totalApiCalls}</CardDescription>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-2xl tabular-nums">
              {formatNumber(summary?.total_api_calls ?? 0)}
            </CardTitle>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>{t.admin.inputTokens}</CardDescription>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-2xl tabular-nums">
              {formatNumber(summary?.total_input_tokens ?? 0)}
            </CardTitle>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>{t.admin.usageRecords}</CardDescription>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-2xl tabular-nums">
              {formatNumber(summary?.total_usage_records ?? 0)}
            </CardTitle>
          </CardContent>
        </Card>
      </div>

      {items.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>{t.admin.userUsageRanking}</CardTitle>
            <CardDescription>{t.admin.userUsageRankingDescription}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-md border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-4 py-3 text-left font-medium">{t.admin.user}</th>
                    <th className="px-4 py-3 text-left font-medium">{t.admin.email}</th>
                    <th className="px-4 py-3 text-right font-medium">{t.admin.inputTokens}</th>
                    <th className="px-4 py-3 text-right font-medium">{t.admin.outputTokens}</th>
                    <th className="px-4 py-3 text-right font-medium">{t.admin.totalTokens}</th>
                    <th className="px-4 py-3 text-right font-medium">{t.admin.apiCallsLabel}</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr
                      key={item.user_id}
                      className="border-b transition-colors hover:bg-muted/30"
                    >
                      <td className="px-4 py-3 font-medium">
                        {item.display_name ?? item.user_id}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{item.email}</td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {formatNumber(item.input_tokens)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {formatNumber(item.output_tokens)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {formatNumber(item.total_tokens)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {formatNumber(item.api_calls)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent>
            <p className="py-8 text-center text-sm text-muted-foreground">
              {t.admin.noUsageData}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
