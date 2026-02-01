"use client";

import { useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/utils";

interface MemorySourceDisplayProps {
  sources: string[];
  className?: string;
}

type MediaType = "photo" | "video" | "audio" | "text" | "document" | "unknown";

const EXTENSION_TYPE_MAP: Record<string, MediaType> = {
  jpg: "photo",
  jpeg: "photo",
  png: "photo",
  gif: "photo",
  webp: "photo",
  bmp: "photo",
  mp4: "video",
  webm: "video",
  mov: "video",
  avi: "video",
  mp3: "audio",
  wav: "audio",
  ogg: "audio",
  m4a: "audio",
  flac: "audio",
  txt: "text",
  md: "text",
  pdf: "document",
  doc: "document",
  docx: "document",
  rtf: "document",
};

function extractExtension(raw: string): string | null {
  const lower = raw.toLowerCase();
  if (lower.startsWith("s3://")) {
    const key = raw.slice(5);
    const last = key.split("/").pop() || "";
    const dot = last.lastIndexOf(".");
    return dot >= 0 ? last.slice(dot + 1).toLowerCase() : null;
  }

  try {
    const parsed = new URL(raw);
    const keyParam = parsed.searchParams.get("object_key");
    if (keyParam) {
      const decoded = decodeURIComponent(keyParam);
      const last = decoded.split("/").pop() || "";
      const dot = last.lastIndexOf(".");
      if (dot >= 0) return last.slice(dot + 1).toLowerCase();
    }
    const last = parsed.pathname.split("/").pop() || "";
    const dot = last.lastIndexOf(".");
    return dot >= 0 ? last.slice(dot + 1).toLowerCase() : null;
  } catch {
    const queryIndex = lower.indexOf("?object_key=");
    if (queryIndex >= 0) {
      const key = raw.slice(queryIndex + "?object_key=".length).split("&")[0];
      const decoded = decodeURIComponent(key);
      const last = decoded.split("/").pop() || "";
      const dot = last.lastIndexOf(".");
      if (dot >= 0) return last.slice(dot + 1).toLowerCase();
    }
    const last = raw.split("/").pop() || "";
    const dot = last.lastIndexOf(".");
    return dot >= 0 ? last.slice(dot + 1).toLowerCase() : null;
  }
}

function getMediaType(url: string, resolvedUrl?: string): MediaType {
  const ext = extractExtension(url) || (resolvedUrl ? extractExtension(resolvedUrl) : null);
  if (ext && EXTENSION_TYPE_MAP[ext]) return EXTENSION_TYPE_MAP[ext];
  return "unknown";
}

function resolveSourceUrl(url: string) {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const lower = url.toLowerCase();
  if (lower.startsWith("s3://")) {
    const withoutScheme = url.slice(5);
    const keyStart = withoutScheme.indexOf("/");
    const key = keyStart >= 0 ? withoutScheme.slice(keyStart + 1) : "";
    return `${apiBase}/api/v1/storage/stream?object_key=${encodeURIComponent(key)}`;
  }
  if (lower.includes("amazonaws.com")) {
    try {
      const parsed = new URL(url);
      const key = parsed.pathname.replace(/^\//, "");
      return `${apiBase}/api/v1/storage/stream?object_key=${encodeURIComponent(key)}`;
    } catch {
      return url;
    }
  }
  return url;
}

export function MemorySourceDisplay({
  sources,
  className,
}: MemorySourceDisplayProps) {
  const [isVisible, setIsVisible] = useState(false);

  const resolvedSources = useMemo(
    () => (sources || []).map((source) => resolveSourceUrl(source)),
    [sources]
  );

  useEffect(() => {
    setIsVisible(false);
    const timer = setTimeout(() => setIsVisible(true), 150);
    return () => {
      clearTimeout(timer);
    };
  }, [sources]);

  if (!sources || sources.length === 0) return null;

  const visualItems = sources
    .map((url, index) => ({
      url,
      resolvedUrl: resolvedSources[index] || url,
      type: getMediaType(url, resolvedSources[index]),
      index,
    }))
    .filter((item) => item.type === "photo" || item.type === "video");

  if (visualItems.length === 0) return null;

  const positionPresets = [
    { top: "2%", left: "6%", rotate: "-2deg", size: "w-32 sm:w-40 md:w-48" },
    { top: "10%", left: "60%", rotate: "2deg", size: "w-36 sm:w-44 md:w-52" },
    { top: "30%", left: "16%", rotate: "-1.5deg", size: "w-30 sm:w-36 md:w-44" },
    { top: "38%", left: "66%", rotate: "1.5deg", size: "w-32 sm:w-40 md:w-48" },
    { top: "54%", left: "36%", rotate: "-0.5deg", size: "w-36 sm:w-44 md:w-52" },
  ];

  return (
    <div className={cn("relative w-full h-52 sm:h-60 md:h-64", className)}>
      {visualItems.map((item, index) => {
        const preset = positionPresets[index % positionPresets.length];
        return (
          <div
            key={`${item.url}-${index}`}
            className={cn(
              "absolute rounded-2xl border border-amber-200/20 bg-stone-950/40 shadow-2xl shadow-amber-900/20 backdrop-blur-sm overflow-hidden",
              "transition-opacity duration-1000 ease-out",
              isVisible ? "opacity-100" : "opacity-0",
              preset.size
            )}
            style={{
              top: preset.top,
              left: preset.left,
              transform: `translate(-10%, 0) rotate(${preset.rotate})`,
            }}
          >
            {item.type === "photo" && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={item.resolvedUrl}
                alt="Memory"
                className="w-full h-full object-cover bg-black/70"
                loading="lazy"
              />
            )}
            {item.type === "video" && (
              <video
                src={item.resolvedUrl}
                controls
                playsInline
                className="w-full h-full object-cover bg-black/70"
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
