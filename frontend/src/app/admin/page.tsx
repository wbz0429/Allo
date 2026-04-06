"use client";

import Link from "next/link";
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

export default function AdminDashboardPage() {
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

  const stats = [
    { label: t.admin.organizations, value: orgUsage.length, href: "/admin/organizations" },
    { label: t.admin.usageRecords, value: summary?.record_count ?? 0 },
    { label: t.admin.inputTokens, value: summary?.total_input_tokens ?? 0, href: "/admin/usage" },
    { label: t.admin.apiCallsLabel, value: summary?.total_api_calls ?? 0, href: "/admin/usage" },
  ];

  const chartBars = orgUsage.slice(0, 10).map((o) => ({
    id: o.org_id,
    label: o.org_name.length > 8 ? `${o.org_name.slice(0, 8)}\u2026` : o.org_name,
    value: o.input_tokens,
    secondaryValue: o.output_tokens,
  }));

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
                  {formatNumber(stat.value)}
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

      {/* Usage chart by org */}
      {chartBars.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t.admin.tokenUsageByOrganization}</CardTitle>
            <CardDescription>{t.admin.topOrganizationsByTokenConsumption}</CardDescription>
          </CardHeader>
          <CardContent>
            <UsageChart
              title=""
              bars={chartBars}
              primaryLabel={t.admin.inputTokensLabel}
              secondaryLabel={t.admin.outputTokensLabel}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
