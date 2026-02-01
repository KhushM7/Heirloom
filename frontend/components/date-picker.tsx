"use client";

import * as React from "react";
import { CalendarIcon } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

interface DatePickerProps {
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}

function formatDisplay(date: Date) {
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

function toIso(date: Date) {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseIso(value?: string) {
  if (!value) return undefined;
  const [year, month, day] = value.split("-").map((part) => Number(part));
  if (!year || !month || !day) return undefined;
  return new Date(year, month - 1, day);
}

export function DatePicker({
  value,
  onChange,
  placeholder = "Select a date",
  className,
  disabled,
}: DatePickerProps) {
  const selectedDate = React.useMemo(() => parseIso(value), [value]);
  const [inputValue, setInputValue] = React.useState(value || "");
  const today = React.useMemo(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate());
  }, []);
  const fromYear = 1900;
  const toYear = today.getFullYear();

  React.useEffect(() => {
    setInputValue(value || "");
  }, [value]);

  const formatDigits = (digits: string) => {
    const trimmed = digits.slice(0, 8);
    const year = trimmed.slice(0, 4);
    const month = trimmed.slice(4, 6);
    const day = trimmed.slice(6, 8);
    if (trimmed.length <= 4) return year;
    if (trimmed.length <= 6) return `${year}-${month}`;
    return `${year}-${month}-${day}`;
  };

  const handleInputChange = (raw: string) => {
    const digits = raw.replace(/\D/g, "");
    setInputValue(formatDigits(digits));
  };

  const commitInput = (raw: string) => {
    const parsed = parseIso(raw);
    if (!parsed) {
      setInputValue(value || "");
      return;
    }
    const clamped = parsed > today ? today : parsed;
    const iso = toIso(clamped);
    setInputValue(iso);
    onChange?.(iso);
  };

  return (
    <Popover>
      <div className={cn("flex w-full items-center gap-2", className)}>
        <input
          type="text"
          inputMode="numeric"
          placeholder={placeholder}
          value={inputValue}
          onChange={(e) => handleInputChange(e.target.value)}
          onBlur={() => commitInput(inputValue)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              commitInput(inputValue);
            }
          }}
          disabled={disabled}
          className={cn(
            "flex h-12 w-full rounded-full border border-amber-200/15 bg-stone-900/40 px-6 text-sm",
            "text-amber-100 placeholder:text-amber-200/30 shadow-xs",
            "focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-amber-200/20",
            "disabled:cursor-not-allowed disabled:opacity-50"
          )}
        />
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            disabled={disabled}
            size="icon"
            className="h-12 w-12 rounded-full border-amber-200/20 bg-stone-900/40 text-amber-100"
          >
            <CalendarIcon className="h-4 w-4" />
          </Button>
        </PopoverTrigger>
      </div>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={selectedDate}
          disabled={(date) => date > today}
          captionLayout="dropdown-buttons"
          fromYear={fromYear}
          toYear={toYear}
          onSelect={(date) => {
            if (!date) return;
            onChange?.(toIso(date));
          }}
          initialFocus
        />
      </PopoverContent>
    </Popover>
  );
}
