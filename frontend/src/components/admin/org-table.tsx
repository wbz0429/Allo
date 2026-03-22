"use client";

import { Badge } from "@/components/ui/badge";
import type { OrgSummary } from "@/core/admin/types";
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
  return (
    <div className={cn("overflow-x-auto rounded-md border", className)}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="px-4 py-3 text-left font-medium">Organization</th>
            <th className="px-4 py-3 text-left font-medium">Members</th>
            <th className="px-4 py-3 text-left font-medium">Tokens Used</th>
            <th className="px-4 py-3 text-left font-medium">API Calls</th>
            <th className="px-4 py-3 text-left font-medium">Created</th>
          </tr>
        </thead>
        <tbody>
          {organizations.length === 0 && (
            <tr>
              <td
                colSpan={5}
                className="px-4 py-8 text-center text-muted-foreground"
              >
                No organizations found
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
                {formatNumber(org.total_tokens)}
              </td>
              <td className="px-4 py-3 tabular-nums">
                {formatNumber(org.total_api_calls)}
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
