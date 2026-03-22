"use client";

import { CheckCircle2Icon } from "lucide-react";
import Link from "next/link";

export function CompletionStep() {
  return (
    <div className="flex flex-col items-center gap-6 py-12">
      <CheckCircle2Icon className="text-primary size-12" />
      <div className="text-center">
        <h2 className="text-lg font-semibold">Setup Complete</h2>
        <p className="text-muted-foreground mt-1 text-sm">
          Your workspace is ready. Start chatting with your AI assistant.
        </p>
      </div>
      <Link
        href="/workspace"
        className="bg-primary text-primary-foreground rounded-md px-4 py-2 text-sm font-medium"
      >
        Go to Workspace
      </Link>
    </div>
  );
}
