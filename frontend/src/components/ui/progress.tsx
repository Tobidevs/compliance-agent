import * as React from "react";

import { cn } from "@/lib/utils";

type ProgressProps = React.HTMLAttributes<HTMLDivElement> & {
  value: number;
  indicatorClassName?: string;
};

function Progress({
  className,
  value,
  indicatorClassName,
  ...props
}: ProgressProps) {
  const boundedValue = Math.max(0, Math.min(100, value));

  return (
    <div
      className={cn(
        "relative h-2.5 w-full overflow-hidden rounded-full bg-black/8",
        className,
      )}
      {...props}
    >
      <div
        className={cn(
          "progress-indicator h-full rounded-full bg-orange-500",
          indicatorClassName,
        )}
        style={{ width: `${boundedValue}%` }}
      />
    </div>
  );
}

export { Progress };
