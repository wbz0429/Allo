"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { getSoul, saveSoul } from "@/core/soul/api";

import { SettingsSection } from "./settings-section";

export function SoulSettingsPage() {
  const [content, setContent] = useState("");
  const [original, setOriginal] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void getSoul().then((data) => {
      setContent(data);
      setOriginal(data);
      setLoading(false);
    });
  }, []);

  const dirty = content !== original;

  const handleSave = useCallback(async () => {
    setSaving(true);
    try {
      await saveSoul(content);
      setOriginal(content);
    } finally {
      setSaving(false);
    }
  }, [content]);

  return (
    <SettingsSection
      title="Personality"
      description="Define your AI assistant's personality, tone, and behavior style. This is injected into every conversation."
    >
      {loading ? (
        <div className="text-muted-foreground text-sm">Loading...</div>
      ) : (
        <div className="space-y-4">
          <Textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="e.g. You are a friendly and concise assistant who speaks in a casual tone..."
            className="min-h-[200px] font-mono text-sm"
          />
          <div className="flex items-center justify-between">
            <p className="text-muted-foreground text-xs">
              Changes take effect on the next conversation.
            </p>
            <Button onClick={handleSave} disabled={!dirty || saving} size="sm">
              {saving ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>
      )}
    </SettingsSection>
  );
}
