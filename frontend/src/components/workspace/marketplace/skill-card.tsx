"use client";

import { DownloadIcon, ExternalLinkIcon, TrashIcon } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

import type { MarketplaceSkill } from "@/core/marketplace/types";

interface SkillCardProps {
  skill: MarketplaceSkill;
  installed: boolean;
  onInstall: (skill: MarketplaceSkill) => void;
  onUninstall: (skill: MarketplaceSkill) => void;
  loading?: boolean;
}

export function SkillCard({
  skill,
  installed,
  onInstall,
  onUninstall,
  loading,
}: SkillCardProps) {
  return (
    <Card className="flex flex-col gap-0 py-0 transition-shadow hover:shadow-md">
      <CardHeader className="flex-1 gap-1 px-4 pt-4">
        <div className="flex items-start justify-between">
          <CardTitle className="text-base">{skill.name}</CardTitle>
          <Badge variant="secondary" className="text-[10px] capitalize">
            {skill.category}
          </Badge>
        </div>
        <CardDescription className="line-clamp-2 text-xs">
          {skill.description}
        </CardDescription>
      </CardHeader>
      <CardFooter className="gap-2 px-4 pb-4">
        <Link
          href={`/workspace/marketplace/skills/${skill.id}`}
          className="mr-auto"
        >
          <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-xs">
            <ExternalLinkIcon className="size-3" />
            Details
          </Button>
        </Link>
        {installed ? (
          <Button
            variant="destructive"
            size="sm"
            className="h-7 gap-1 px-2 text-xs"
            disabled={loading}
            onClick={() => onUninstall(skill)}
          >
            <TrashIcon className="size-3" />
            Uninstall
          </Button>
        ) : (
          <Button
            variant="default"
            size="sm"
            className={cn("h-7 gap-1 px-2 text-xs")}
            disabled={loading}
            onClick={() => onInstall(skill)}
          >
            <DownloadIcon className="size-3" />
            Install
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
