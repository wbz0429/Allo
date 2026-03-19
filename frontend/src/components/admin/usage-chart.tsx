"use client";

import { cn } from "@/lib/utils";

interface UsageChartBar {
  label: string;
  value: number;
  secondaryValue?: number;
}

interface UsageChartProps {
  title: string;
  bars: UsageChartBar[];
  primaryLabel?: string;
  secondaryLabel?: string;
  className?: string;
  formatValue?: (value: number) => string;
}

function defaultFormat(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return String(value);
}

export function UsageChart({
  title,
  bars,
  primaryLabel = "Input",
  secondaryLabel = "Output",
  className,
  formatValue = defaultFormat,
}: UsageChartProps) {
  const maxValue = Math.max(
    ...bars.map((b) => b.value + (b.secondaryValue ?? 0)),
    1,
  );

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">{title}</h3>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-primary" />
            {primaryLabel}
          </span>
          {bars.some((b) => b.secondaryValue !== undefined) && (
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-sm bg-primary/40" />
              {secondaryLabel}
            </span>
          )}
        </div>
      </div>
      <div className="flex items-end gap-1.5" style={{ height: 160 }}>
        {bars.map((bar) => {
          const total = bar.value + (bar.secondaryValue ?? 0);
          const pct = (total / maxValue) * 100;
          const primaryPct =
            total > 0 ? (bar.value / total) * 100 : 0;

          return (
            <div
              key={bar.label}
              className="group relative flex flex-1 flex-col items-center"
              style={{ height: "100%" }}
            >
              {/* Tooltip */}
              <div className="pointer-events-none absolute -top-8 z-10 hidden rounded bg-popover px-2 py-1 text-xs shadow-md group-hover:block">
                {formatValue(total)}
              </div>
              {/* Bar container */}
              <div
                className="flex w-full flex-col justify-end"
                style={{ height: "100%" }}
              >
                <div
                  className="relative w-full overflow-hidden rounded-t-sm transition-all"
                  style={{ height: `${Math.max(pct, 2)}%` }}
                >
                  {/* Primary portion */}
                  <div
                    className="absolute bottom-0 w-full bg-primary"
                    style={{ height: `${primaryPct}%` }}
                  />
                  {/* Secondary portion */}
                  <div
                    className="absolute top-0 w-full bg-primary/40"
                    style={{ height: `${100 - primaryPct}%` }}
                  />
                </div>
              </div>
              {/* Label */}
              <span className="mt-1.5 text-[10px] leading-none text-muted-foreground">
                {bar.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
