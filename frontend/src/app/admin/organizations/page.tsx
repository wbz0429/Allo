"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

import { OrgTable } from "@/components/admin/org-table";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { listOrganizations } from "@/core/admin/api";
import type { OrgSummary } from "@/core/admin/types";

export default function AdminOrganizationsPage() {
  const [orgs, setOrgs] = useState<OrgSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listOrganizations()
      .then(setOrgs)
      .catch((err: Error) => {
        toast.error(err.message);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">Organizations</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage all organizations on the platform
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Organizations</CardTitle>
          <CardDescription>
            {loading ? "Loading\u2026" : `${orgs.length} organization${orgs.length !== 1 ? "s" : ""}`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex flex-col gap-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : (
            <OrgTable organizations={orgs} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
