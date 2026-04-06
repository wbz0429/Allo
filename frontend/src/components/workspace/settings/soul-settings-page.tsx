"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useI18n } from "@/core/i18n/hooks";
import { getSoul, saveSoul } from "@/core/soul/api";

import { SettingsSection } from "./settings-section";

export function SoulSettingsPage() {
  const { t } = useI18n();
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
      title={t.soul.title}
      description={t.soul.description}
    >
      {loading ? (
        <div className="text-muted-foreground text-sm">{t.common.loading}</div>
      ) : (
        <div className="space-y-4">
          <Textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={t.soul.placeholder}
            className="min-h-[200px] font-mono text-sm"
          />
          <div className="flex items-center justify-between">
            <p className="text-muted-foreground text-xs">
              {t.soul.hint}
            </p>
            <Button onClick={handleSave} disabled={!dirty || saving} size="sm">
              {saving ? t.soul.saving : t.common.save}
            </Button>
          </div>
        </div>
      )}
    </SettingsSection>
  );
}
