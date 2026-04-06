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
import { useI18n } from "@/core/i18n/hooks";
import { useCreateKnowledgeBase, useKnowledgeBases } from "@/core/knowledge/hooks";

export default function KnowledgeBasesPage() {
  const { t } = useI18n();
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
      toast.success(t.knowledge.created);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : t.knowledge.createFailed,
      );
    }
  }, [name, description, createMutation]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b px-6 py-4">
        <div className="flex items-center gap-2">
          <BookOpenIcon className="text-muted-foreground size-5" />
          <h1 className="text-lg font-semibold">{t.knowledge.title}</h1>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <PlusIcon className="mr-1 size-4" />
              {t.knowledge.newButton}
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t.knowledge.createTitle}</DialogTitle>
              <DialogDescription>
                {t.knowledge.createDescription}
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-4 py-2">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="kb-name" className="text-sm font-medium">
                  {t.knowledge.name}
                </label>
                <Input
                  id="kb-name"
                  placeholder={t.knowledge.namePlaceholder}
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
                  {t.knowledge.description}
                </label>
                <Input
                  id="kb-description"
                  placeholder={t.knowledge.descriptionPlaceholder}
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
                {t.common.cancel}
              </Button>
              <Button
                onClick={handleCreate}
                disabled={!name.trim() || createMutation.isPending}
              >
                {createMutation.isPending ? t.knowledge.creating : t.common.create}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="text-muted-foreground flex items-center justify-center py-12 text-sm">
            {t.common.loading}
          </div>
        ) : knowledgeBases.length === 0 ? (
          <div className="text-muted-foreground flex flex-col items-center justify-center gap-2 py-12 text-sm">
            <BookOpenIcon className="size-10 opacity-30" />
            <p>{t.knowledge.empty}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDialogOpen(true)}
            >
              <PlusIcon className="mr-1 size-4" />
              {t.knowledge.createFirst}
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
