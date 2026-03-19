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
import { UsageChart } from "@/components/admin/usage-chart";
import { getUsageByOrg, getUsageSummary } from "@/core/admin/api";
import type { OrgUsageBreakdown, UsageSummary } from "@/core/admin/types";

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export default function AdminUsagePage() {
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
        toast.error(err.message);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-2xl font-semibold">Usage</h1>
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
    label: o.org_name.length > 8 ? `${o.org_name.slice(0, 8)}\u2026` : o.org_name,
    value: o.input_tokens,
    secondaryValue: o.output_tokens,
  }));

  const apiCallBars = orgUsage.map((o) => ({
    label: o.org_name.length > 8 ? `${o.org_name.slice(0, 8)}\u2026` : o.org_name,
    value: o.api_calls,
  }));

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold">Usage</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Global platform usage statistics
        </p>
      </div>

      {/* Summary stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardDescription>Total Tokens</CardDescription>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-2xl tabular-nums">
              {formatNumber(summary?.total_tokens ?? 0)}
            </CardTitle>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Total API Calls</CardDescription>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-2xl tabular-nums">
              {formatNumber(summary?.total_api_calls ?? 0)}
            </CardTitle>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Tokens Today</CardDescription>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-2xl tabular-nums">
              {formatNumber(summary?.tokens_today ?? 0)}
            </CardTitle>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>API Calls Today</CardDescription>
          </CardHeader>
          <CardContent>
            <CardTitle className="text-2xl tabular-nums">
              {formatNumber(summary?.api_calls_today ?? 0)}
            </CardTitle>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Token Usage by Organization</CardTitle>
            <CardDescription>Input and output token breakdown</CardDescription>
          </CardHeader>
          <CardContent>
            {tokenBars.length > 0 ? (
              <UsageChart
                title=""
                bars={tokenBars}
                primaryLabel="Input tokens"
                secondaryLabel="Output tokens"
              />
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No usage data yet
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>API Calls by Organization</CardTitle>
            <CardDescription>Total API call volume</CardDescription>
          </CardHeader>
          <CardContent>
            {apiCallBars.length > 0 ? (
              <UsageChart
                title=""
                bars={apiCallBars}
                primaryLabel="API calls"
              />
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No usage data yet
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Breakdown table */}
      {orgUsage.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Detailed Breakdown</CardTitle>
            <CardDescription>Usage per organization</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-md border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-4 py-3 text-left font-medium">Organization</th>
                    <th className="px-4 py-3 text-right font-medium">Input Tokens</th>
                    <th className="px-4 py-3 text-right font-medium">Output Tokens</th>
                    <th className="px-4 py-3 text-right font-medium">API Calls</th>
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
