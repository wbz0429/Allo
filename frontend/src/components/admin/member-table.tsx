"use client";

import { useCallback, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

import type { OrgMember } from "@/core/org/types";

interface MemberTableProps {
  members: OrgMember[];
  className?: string;
  onInvite?: (email: string) => Promise<void>;
  onRemove?: (userId: string) => Promise<void>;
  onRoleChange?: (userId: string, role: "admin" | "member") => Promise<void>;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function MemberTable({
  members,
  className,
  onInvite,
  onRemove,
  onRoleChange,
}: MemberTableProps) {
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviting, setInviting] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);

  const handleInvite = useCallback(async () => {
    if (!inviteEmail.trim() || !onInvite) return;
    setInviting(true);
    try {
      await onInvite(inviteEmail.trim());
      setInviteEmail("");
    } finally {
      setInviting(false);
    }
  }, [inviteEmail, onInvite]);

  const handleRemove = useCallback(
    async (userId: string) => {
      if (!onRemove) return;
      setRemovingId(userId);
      try {
        await onRemove(userId);
      } finally {
        setRemovingId(null);
      }
    },
    [onRemove],
  );

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      {/* Invite row */}
      {onInvite && (
        <div className="flex items-center gap-2">
          <Input
            type="email"
            placeholder="Email address"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void handleInvite();
            }}
            className="max-w-sm"
          />
          <Button
            size="sm"
            disabled={!inviteEmail.trim() || inviting}
            onClick={() => void handleInvite()}
          >
            {inviting ? "Inviting\u2026" : "Invite"}
          </Button>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="px-4 py-3 text-left font-medium">Member</th>
              <th className="px-4 py-3 text-left font-medium">Role</th>
              <th className="px-4 py-3 text-left font-medium">Joined</th>
              <th className="px-4 py-3 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {members.length === 0 && (
              <tr>
                <td
                  colSpan={4}
                  className="px-4 py-8 text-center text-muted-foreground"
                >
                  No members found
                </td>
              </tr>
            )}
            {members.map((member) => (
              <tr
                key={member.user_id}
                className="border-b transition-colors hover:bg-muted/30"
              >
                <td className="px-4 py-3">
                  <div className="flex flex-col gap-0.5">
                    <span className="font-medium">{member.name}</span>
                    <span className="text-xs text-muted-foreground">
                      {member.email}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  {onRoleChange ? (
                    <Select
                      value={member.role}
                      onValueChange={(value) =>
                        void onRoleChange(
                          member.user_id,
                          value as "admin" | "member",
                        )
                      }
                    >
                      <SelectTrigger size="sm" className="w-28">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="admin">Admin</SelectItem>
                        <SelectItem value="member">Member</SelectItem>
                      </SelectContent>
                    </Select>
                  ) : (
                    <Badge
                      variant={
                        member.role === "admin" ? "default" : "secondary"
                      }
                    >
                      {member.role}
                    </Badge>
                  )}
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {formatDate(member.joined_at)}
                </td>
                <td className="px-4 py-3 text-right">
                  {onRemove && (
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                        >
                          Remove
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Remove member</DialogTitle>
                          <DialogDescription>
                            Are you sure you want to remove {member.name} from
                            the organization? This action cannot be undone.
                          </DialogDescription>
                        </DialogHeader>
                        <DialogFooter>
                          <DialogClose asChild>
                            <Button variant="outline">Cancel</Button>
                          </DialogClose>
                          <Button
                            variant="destructive"
                            disabled={removingId === member.user_id}
                            onClick={() => void handleRemove(member.user_id)}
                          >
                            {removingId === member.user_id
                              ? "Removing\u2026"
                              : "Remove"}
                          </Button>
                        </DialogFooter>
                      </DialogContent>
                    </Dialog>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
