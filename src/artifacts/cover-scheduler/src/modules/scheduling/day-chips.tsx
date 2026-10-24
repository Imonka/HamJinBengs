import { WEEKDAYS } from "@/lib/time";
import { cn } from "@/lib/utils";

export function DayChips({ value, onChange, testPrefix }: { value: number[]; onChange: (v: number[]) => void; testPrefix: string }) {
  return (
    <div className="flex flex-wrap gap-1">
      {WEEKDAYS.map((d, i) => {
        const on = value.includes(i);
        return (
          <button key={d} type="button" onClick={() => onChange(on ? value.filter((x) => x !== i) : [...value, i].sort())} data-testid={`${testPrefix}-${i}`}
            className={cn("h-8 w-11 rounded-md text-xs font-medium border transition-colors", on ? "bg-primary text-primary-foreground border-primary" : "bg-card text-muted-foreground hover:border-foreground/40")}>{d}</button>
        );
      })}
    </div>
  );
}

