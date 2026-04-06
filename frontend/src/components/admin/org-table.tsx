"use client";

import { Badge } from "@/components/ui/badge";
import type { OrgSummary } from "@/core/admin/types";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";


interface OrgTableProps {
  organizations: OrgSummary[];
  className?: string;
  onSelect?: (org: OrgSummary) => void;
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function OrgTable({ organizations, className, onSelect }: OrgTableProps) {
  const { t } = useI18n();

  return (
    <div className={cn("overflow-x-auto rounded-md border", className)}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-4 py-3 text-left font-medium">{t.admin.organization}</th>
            <th className="px-4 py-3 text-left font-medium">{t.admin.members}</th>
            <th className="px-4 py-3 text-left font-medium">{t.admin.tokensUsed}</th>
            <th className="px-4 py-3 text-left font-medium">{t.admin.apiCallsLabel}</th>
            <th className="px-4 py-3 text-left font-medium">{t.admin.created}</th>
          </tr>
        </thead>
        <tbody>
          {organizations.length === 0 && (
            <tr>
              <td
                colSpan={5}
                className="px-4 py-8 text-center text-muted-foreground"
              >
                {t.admin.noOrganizationsFound}
              </td>
            </tr>
          )}
          {organizations.map((org) => (
            <tr
              key={org.id}
              className={cn(
                "border-b transition-colors hover:bg-muted/30",
                onSelect && "cursor-pointer",
              )}
              onClick={() => onSelect?.(org)}
            >
              <td className="px-4 py-3">
                <div className="flex flex-col gap-0.5">
                  <span className="font-medium">{org.name}</span>
                  <span className="text-xs text-muted-foreground">
                    {org.slug}
                  </span>
                </div>
              </td>
              <td className="px-4 py-3">
                <Badge variant="secondary">{org.member_count}</Badge>
              </td>
              <td className="px-4 py-3 tabular-nums">
                {formatNumber(0)}
              </td>
              <td className="px-4 py-3 tabular-nums">
                {formatNumber(0)}
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {formatDate(org.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
