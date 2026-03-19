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

import type { MarketplaceTool } from "@/core/marketplace/types";

interface ToolCardProps {
  tool: MarketplaceTool;
  installed: boolean;
  onInstall: (tool: MarketplaceTool) => void;
  onUninstall: (tool: MarketplaceTool) => void;
  loading?: boolean;
}

export function ToolCard({
  tool,
  installed,
  onInstall,
  onUninstall,
  loading,
}: ToolCardProps) {
  return (
    <Card className="flex flex-col gap-0 py-0 transition-shadow hover:shadow-md">
      <CardHeader className="flex-1 gap-1 px-4 pt-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl" role="img" aria-label={tool.name}>
              {tool.icon}
            </span>
            <CardTitle className="text-base">{tool.name}</CardTitle>
          </div>
          <Badge variant="secondary" className="text-[10px] capitalize">
            {tool.category}
          </Badge>
        </div>
        <CardDescription className="line-clamp-2 text-xs">
          {tool.description}
        </CardDescription>
      </CardHeader>
      <CardFooter className="gap-2 px-4 pb-4">
        <Link
          href={`/workspace/marketplace/tools/${tool.id}`}
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
            onClick={() => onUninstall(tool)}
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
            onClick={() => onInstall(tool)}
          >
            <DownloadIcon className="size-3" />
            Install
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
