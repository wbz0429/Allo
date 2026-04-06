"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { UsageChart } from "@/components/admin/usage-chart";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getUsageByOrg, getUsageSummary } from "@/core/admin/api";
import type { OrgUsageBreakdown, UsageSummary } from "@/core/admin/types";
import { useI18n } from "@/core/i18n/hooks";

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export default function AdminUsagePage() {
  const { t } = useI18n();
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [orgUsage, setOrgUsage] = useState<OrgUsageBreakdown[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getUsageSummary(), getUsageByOrg()])
      .then(([s, u]) => {
        setSummary(s);
        setOrgUsage(u);
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

  const tokenBars = orgUsage.map((o) => ({
    id: `tokens-${o.org_id}`,
    label: o.org_name.length > 8 ? `${o.org_name.slice(0, 8)}…` : o.org_name,
    value: o.input_tokens,
    secondaryValue: o.output_tokens,
  }));

  const apiCallBars = orgUsage.map((o) => ({
    id: `calls-${o.org_id}`,
    label: o.org_name.length > 8 ? `${o.org_name.slice(0, 8)}…` : o.org_name,
    value: o.api_calls,
  }));

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
            <CardDescription>{t.admin.tokensToday}</CardDescription>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-2xl tabular-nums">
              {formatNumber(summary?.total_input_tokens ?? 0)}
            </CardTitle>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>{t.admin.apiCallsToday}</CardDescription>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-2xl tabular-nums">
              {formatNumber(summary?.record_count ?? 0)}
            </CardTitle>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t.admin.tokenUsageByOrganization}</CardTitle>
            <CardDescription>{t.admin.topOrganizationsByTokenConsumption}</CardDescription>
          </CardHeader>
          <CardContent>
            {tokenBars.length > 0 ? (
              <UsageChart
                title=""
                bars={tokenBars}
                primaryLabel={t.admin.inputTokensLabel}
                secondaryLabel={t.admin.outputTokensLabel}
              />
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                {t.admin.noUsageData}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t.admin.apiCallsByOrganization}</CardTitle>
            <CardDescription>{t.admin.totalApiCallVolume}</CardDescription>
          </CardHeader>
          <CardContent>
            {apiCallBars.length > 0 ? (
              <UsageChart
                title=""
                bars={apiCallBars}
                primaryLabel={t.admin.apiCallsLabel}
              />
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                {t.admin.noUsageData}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {orgUsage.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t.admin.detailedBreakdown}</CardTitle>
            <CardDescription>{t.admin.usagePerOrganization}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-md border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-4 py-3 text-left font-medium">{t.admin.organization}</th>
                    <th className="px-4 py-3 text-right font-medium">{t.admin.inputTokens}</th>
                    <th className="px-4 py-3 text-right font-medium">{t.admin.outputTokens}</th>
                    <th className="px-4 py-3 text-right font-medium">{t.admin.apiCallsLabel}</th>
                  </tr>
                </thead>
                <tbody>
                  {orgUsage.map((o) => (
                    <tr
                      key={o.org_id}
                      className="border-b transition-colors hover:bg-muted/30"
                    >
                      <td className="px-4 py-3 font-medium">{o.org_name}</td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {formatNumber(o.input_tokens)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {formatNumber(o.output_tokens)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {formatNumber(o.api_calls)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
