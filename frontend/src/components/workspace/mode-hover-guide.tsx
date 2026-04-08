"use client";

import { useI18n } from "@/core/i18n/hooks";
import type { Translations } from "@/core/i18n/locales/types";

import { Tooltip } from "./tooltip";

export type AgentMode = "autonomous" | "precise" | "express";

function getModeLabelKey(
  mode: AgentMode,
): keyof Pick<
  Translations["inputBox"],
  "autonomousMode" | "preciseMode" | "expressMode"
> {
  switch (mode) {
    case "autonomous":
      return "autonomousMode";
    case "precise":
      return "preciseMode";
    case "express":
      return "expressMode";
  }
}

function getModeDescriptionKey(
  mode: AgentMode,
): keyof Pick<
  Translations["inputBox"],
  "autonomousModeDescription" | "preciseModeDescription" | "expressModeDescription"
> {
  switch (mode) {
    case "autonomous":
      return "autonomousModeDescription";
    case "precise":
      return "preciseModeDescription";
    case "express":
      return "expressModeDescription";
  }
}

export function ModeHoverGuide({
  mode,
  children,
  showTitle = true,
}: {
  mode: AgentMode;
  children: React.ReactNode;
  /** When true, tooltip shows "ModeName: Description". When false, only description. */
  showTitle?: boolean;
}) {
  const { t } = useI18n();
  const label = t.inputBox[getModeLabelKey(mode)];
  const description = t.inputBox[getModeDescriptionKey(mode)];
  const content = showTitle ? `${label}: ${description}` : description;

  return <Tooltip content={content}>{children}</Tooltip>;
}
