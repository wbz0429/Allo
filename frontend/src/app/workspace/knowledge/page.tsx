"use client";

import { BookOpenIcon, PlusIcon } from "lucide-react";
import Link from "next/link";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { KbCard } from "@/components/workspace/knowledge/kb-card";
import { useCreateKnowledgeBase, useKnowledgeBases } from "@/core/knowledge/hooks";

export default function KnowledgeBasesPage() {
  const { knowledgeBases, isLoading } = useKnowledgeBases();
  const createMutation = useCreateKnowledgeBase();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const handleCreate = useCallback(async () => {
    if (!name.trim()) return;
    try {
      await createMutation.mutateAsync({
        name: name.trim(),
        description: description.trim(),
      });
      setDialogOpen(false);
      setName("");
      setDescription("");
      toast.success("Knowledge base created");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to create knowledge base",
      );
    }
  }, [name, description, createMutation]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-2">
          <BookOpenIcon className="text-muted-foreground size-5" />
          <h1 className="text-lg font-semibold">Knowledge Bases</h1>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <PlusIcon className="mr-1 size-4" />
              New
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Knowledge Base</DialogTitle>
              <DialogDescription>
                A knowledge base stores documents for retrieval-augmented
                generation.
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-4 py-2">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="kb-name" className="text-sm font-medium">
                  Name
                </label>
                <Input
                  id="kb-name"
                  placeholder="e.g. Product Documentation"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoFocus
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="kb-description"
                  className="text-sm font-medium"
                >
                  Description
                </label>
                <Input
                  id="kb-description"
                  placeholder="Optional description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={handleCreate}
                disabled={!name.trim() || createMutation.isPending}
              >
                {createMutation.isPending ? "Creating..." : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="text-muted-foreground flex items-center justify-center py-12 text-sm">
            Loading...
          </div>
        ) : knowledgeBases.length === 0 ? (
          <div className="text-muted-foreground flex flex-col items-center justify-center gap-2 py-12 text-sm">
            <BookOpenIcon className="size-10 opacity-30" />
            <p>No knowledge bases yet</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDialogOpen(true)}
            >
              <PlusIcon className="mr-1 size-4" />
              Create your first
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {knowledgeBases.map((kb) => (
              <Link
                key={kb.id}
                href={`/workspace/knowledge/${kb.id}`}
                className="block"
              >
                <KbCard knowledgeBase={kb} />
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
