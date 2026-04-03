import { formatDistanceToNow } from "date-fns";
import { enUS as dateFnsEnUS, zhCN as dateFnsZhCN } from "date-fns/locale";

import { detectLocale, type Locale } from "@/core/i18n";
import { getLocaleFromCookie } from "@/core/i18n/cookies";

function getDateFnsLocale(locale: Locale) {
  switch (locale) {
    case "zh-CN":
      return dateFnsZhCN;
    case "en-US":
    default:
      return dateFnsEnUS;
  }
}

export function formatTimeAgo(date: Date | string | number, locale?: Locale): string {
  // Guard against empty or unparseable values (e.g. new-user memory with "")
  if (!date && date !== 0) return "—";
  const parsed = date instanceof Date ? date : new Date(date);
  if (isNaN(parsed.getTime())) return "—";

  const effectiveLocale =
    locale ??
    (getLocaleFromCookie() as Locale | null) ??
    // Fallback when cookie is missing (or on first render)
    detectLocale();
  return formatDistanceToNow(parsed, {
    addSuffix: true,
    locale: getDateFnsLocale(effectiveLocale),
  });
}
