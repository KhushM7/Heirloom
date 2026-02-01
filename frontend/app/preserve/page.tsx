"use client";

import React from "react";
import { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import { FileUpload } from "@/components/file-upload";
import {
  UploadProgress,
  UploadItem,
  UploadStatus,
} from "@/components/upload-progress";
import { MediaAssetCard } from "@/components/media-asset-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AmbientParticles } from "@/components/ambient-particles";
import { DatePicker } from "@/components/date-picker";
import {
  initUpload,
  uploadToS3,
  confirmUpload,
  getMediaAssets,
  MediaAssetOut,
  createProfile,
  getMemoryUnits,
  updateMemoryUnits,
  cloneVoiceSample,
} from "@/lib/api";
import useSWR from "swr";
import { useProfile } from "@/lib/profile-context";
import { cn } from "@/lib/utils";

export default function PreservePage() {
  const { profileId, setProfileId, profileName, setProfileName } = useProfile();
  const [profileNameInput, setProfileNameInput] = useState(profileName);
  const [profileDobInput, setProfileDobInput] = useState("");
  const [isProfileSet, setIsProfileSet] = useState(Boolean(profileId));
  const [profileError, setProfileError] = useState("");
  const [isCreatingProfile, setIsCreatingProfile] = useState(false);
  const [voiceSample, setVoiceSample] = useState<File | null>(null);
  const [voiceError, setVoiceError] = useState("");
  const [isCloningVoice, setIsCloningVoice] = useState(false);
  const [uploadQueue, setUploadQueue] = useState<UploadItem[]>([]);
  const displayName = profileName || "Archive";

  useEffect(() => {
    setIsProfileSet(Boolean(profileId));
    setProfileNameInput(profileName);
    setProfileDobInput("");
  }, [profileId, profileName]);

  const { data: mediaAssets, mutate: mutateAssets } = useSWR<MediaAssetOut[]>(
    isProfileSet && profileId ? `/profiles/${profileId}/media-assets` : null,
    () => getMediaAssets(profileId),
    { revalidateOnFocus: false }
  );

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profileNameInput.trim()) return;
    setProfileError("");
    setIsCreatingProfile(true);
    setVoiceError("");

    let voiceId: string | undefined;
    if (voiceSample) {
      try {
        setIsCloningVoice(true);
        const voiceResponse = await cloneVoiceSample(
          voiceSample,
          profileNameInput.trim()
        );
        voiceId = voiceResponse.voice_id;
      } catch (error) {
        setVoiceError(
          error instanceof Error ? error.message : "Failed to clone voice."
        );
        setIsCreatingProfile(false);
        setIsCloningVoice(false);
        return;
      } finally {
        setIsCloningVoice(false);
      }
    }

    try {
      const created = await createProfile({
        name: profileNameInput.trim(),
        date_of_birth: profileDobInput.trim() || undefined,
        voice_id: voiceId,
      });
      setProfileId(created.id);
      setProfileName(created.name || profileNameInput.trim());
      setIsProfileSet(true);
    } catch (error) {
      setProfileError(
        error instanceof Error ? error.message : "Failed to create profile."
      );
    } finally {
      setIsCreatingProfile(false);
    }
  };

  const updateUploadStatus = useCallback(
    (id: string, updates: Partial<UploadItem>) => {
      setUploadQueue((prev) =>
        prev.map((item) => (item.id === id ? { ...item, ...updates } : item))
      );
    },
    []
  );

  const uploadFile = useCallback(
    async (item: UploadItem) => {
      const { id, file } = item;

      try {
        if (!item.title?.trim() || !item.location?.trim() || !item.date?.trim()) {
          updateUploadStatus(id, {
            status: "error",
            error: "Title, location, and date are required before upload.",
          });
          return;
        }
        updateUploadStatus(id, { status: "uploading", progress: 10 });

        const initResponse = await initUpload({
          profile_id: profileId,
          file_name: file.name,
          mime_type: file.type,
          bytes: file.size,
        });

        updateUploadStatus(id, { progress: 30 });

        await uploadToS3(initResponse.upload_url, file);

        updateUploadStatus(id, { progress: 70 });

        const confirmResponse = await confirmUpload({
          profile_id: profileId,
          object_id: initResponse.object_id,
          object_key: initResponse.object_key,
          file_name: file.name,
          mime_type: file.type,
          bytes: file.size,
        });

        updateUploadStatus(id, { status: "processing", progress: 90 });

        const hasMetadata = true;
        if (hasMetadata) {
          const deadline = Date.now() + 90_000;
          let hasUnits = false;
          while (Date.now() < deadline) {
            const current = await getMemoryUnits(confirmResponse.media_asset_id);
            if (current.length > 0) {
              hasUnits = true;
              break;
            }
            await new Promise((resolve) => setTimeout(resolve, 3000));
          }
          if (hasUnits) {
            await updateMemoryUnits(confirmResponse.media_asset_id, {
              title: item.title?.trim() || undefined,
              description: item.description?.trim() || undefined,
              places: item.location?.trim() ? [item.location.trim()] : undefined,
              dates: item.date?.trim() ? [item.date.trim()] : undefined,
            });
          } else {
            updateUploadStatus(id, {
              status: "error",
              error: "Upload succeeded, but metadata could not be saved yet.",
            });
            return;
          }
        }

        updateUploadStatus(id, { status: "complete", progress: 100 });
        mutateAssets();
      } catch (error) {
        updateUploadStatus(id, {
          status: "error",
          error: error instanceof Error ? error.message : "Upload failed",
        });
      }
    },
    [profileId, updateUploadStatus, mutateAssets]
  );

  const handleFilesSelected = useCallback(
    (files: File[]) => {
      const newItems: UploadItem[] = files.map((file) => ({
        id: `${file.name}-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        file,
        status: "pending" as UploadStatus,
        progress: 0,
      }));

      setUploadQueue((prev) => [...prev, ...newItems]);
    },
    []
  );

  const handleUploadItem = useCallback(
    (id: string) => {
      const item = uploadQueue.find((entry) => entry.id === id);
      if (!item) return;
      uploadFile(item);
    },
    [uploadFile, uploadQueue]
  );

  const handleUpdateItem = useCallback((id: string, updates: Partial<UploadItem>) => {
    setUploadQueue((prev) =>
      prev.map((item) => (item.id === id ? { ...item, ...updates } : item))
    );
  }, []);

  const handleRemoveFromQueue = (id: string) => {
    setUploadQueue((prev) => prev.filter((item) => item.id !== id));
  };

  // Profile Setup Screen
  if (!isProfileSet) {
    return (
      <div className="min-h-screen bg-stone-950 text-amber-100 relative overflow-hidden">
        {/* Ambient background */}
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse at 50% 30%, rgba(60, 40, 20, 0.4) 0%, rgba(15, 10, 5, 1) 70%)",
          }}
        />

        {/* Vignette */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            boxShadow: "inset 0 0 200px 100px rgba(0, 0, 0, 0.8)",
          }}
        />

        <AmbientParticles />

        {/* Back button */}
        <div className="absolute top-6 left-6 z-20">
          <Link
            href="/"
            className="flex items-center gap-2 text-amber-200/50 hover:text-amber-200/80 transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
            <span className="text-sm">Return</span>
          </Link>
        </div>

        <main className="relative z-10 min-h-screen flex flex-col items-center justify-center px-6">
          <div className="max-w-md w-full text-center">
            {/* Decorative element */}
            <div className="mb-8 flex justify-center">
              <div
                className="w-20 h-0.5"
                style={{
                  background:
                    "linear-gradient(90deg, transparent, rgba(212, 165, 116, 0.5), transparent)",
                }}
              />
            </div>

            <h1 className="font-serif text-3xl md:text-4xl text-amber-100 mb-4">
              Preserve a Legacy
            </h1>

            <p className="text-amber-200/60 mb-12 leading-relaxed">
              Create an archive for your ancestor. Their photographs, letters,
              and recordings will be carefully preserved for future generations.
            </p>

            <form onSubmit={handleProfileSubmit} className="space-y-6">
              <div className="relative">
                <Input
                  type="text"
                  placeholder="Enter their name..."
                  value={profileNameInput}
                  onChange={(e) => setProfileNameInput(e.target.value)}
                  className="bg-stone-900/50 border-amber-200/20 text-amber-100 placeholder:text-amber-200/30 h-14 text-center text-lg font-serif focus:border-amber-200/40 focus:ring-amber-200/20"
                  required
                />
              </div>

              <DatePicker
                value={profileDobInput}
                onChange={setProfileDobInput}
                placeholder="Date of birth (optional)"
              />

              <div className="space-y-2 text-left">
                <label className="block text-xs uppercase tracking-[0.2em] text-amber-200/40 font-serif">
                  Voice Sample (optional)
                </label>
                <input
                  type="file"
                  accept="audio/*"
                  onChange={(e) => {
                    const file = e.target.files?.[0] || null;
                    setVoiceSample(file);
                    setVoiceError("");
                  }}
                  className={cn(
                    "w-full text-xs text-amber-100/70",
                    "file:mr-3 file:py-2 file:px-4 file:rounded-md",
                    "file:border file:border-amber-200/20 file:bg-stone-900/50",
                    "file:text-amber-100/80 file:font-serif file:text-xs",
                    "hover:file:bg-stone-900/70 transition"
                  )}
                />
                {voiceSample && (
                  <p className="text-xs text-amber-200/50 font-serif">
                    Selected: {voiceSample.name}
                  </p>
                )}
                {voiceError && (
                  <p className="text-xs text-red-300/80">{voiceError}</p>
                )}
              </div>

              <Button
                type="submit"
                disabled={
                  isCreatingProfile || isCloningVoice || !profileNameInput.trim()
                }
                className="w-full h-12 bg-gradient-to-r from-amber-900/80 to-amber-800/80 hover:from-amber-800/80 hover:to-amber-700/80 border border-amber-200/20 text-amber-100 font-serif text-lg disabled:opacity-40"
              >
                {isCloningVoice
                  ? "Capturing Voice..."
                  : isCreatingProfile
                  ? "Creating..."
                  : "Create Archive"}
              </Button>
              {profileError && (
                <p className="text-xs text-red-300/80">{profileError}</p>
              )}
            </form>

            {/* Decorative element */}
            <div className="mt-12 flex justify-center">
              <div
                className="w-20 h-0.5"
                style={{
                  background:
                    "linear-gradient(90deg, transparent, rgba(212, 165, 116, 0.3), transparent)",
                }}
              />
            </div>
          </div>
        </main>
      </div>
    );
  }

  // Archive / Upload Screen
  return (
    <div className="min-h-screen bg-stone-950 text-amber-100 relative overflow-hidden">
      {/* Ambient background */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at 50% 0%, rgba(60, 40, 20, 0.3) 0%, rgba(15, 10, 5, 1) 60%)",
        }}
      />

      {/* Vignette */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          boxShadow: "inset 0 0 200px 80px rgba(0, 0, 0, 0.7)",
        }}
      />

      <AmbientParticles />

      {/* Header */}
      <header className="relative z-20 py-6 px-6 border-b border-amber-200/10">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-2 text-amber-200/50 hover:text-amber-200/80 transition-colors"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
            <span className="text-sm">Return Home</span>
          </Link>

          <Link
            href="/discover"
            className="text-sm text-amber-200/60 hover:text-amber-200 transition-colors"
          >
            Discover Stories
          </Link>
        </div>
      </header>

      <main className="relative z-10 max-w-6xl mx-auto px-6 py-12">
        {/* Profile Header */}
        <div className="mb-12 text-center">
          {/* Avatar */}
          <div className="relative inline-block mb-6">
            <div
              className="w-20 h-20 rounded-full flex items-center justify-center"
              style={{
                background:
                  "linear-gradient(135deg, rgba(139, 115, 85, 0.5) 0%, rgba(100, 80, 60, 0.5) 100%)",
                border: "2px solid rgba(212, 165, 116, 0.3)",
                boxShadow: "0 0 30px rgba(255, 200, 150, 0.15)",
              }}
            >
              <span className="font-serif text-3xl text-amber-100">
            {displayName.charAt(0).toUpperCase()}
              </span>
            </div>
          </div>

          <h1 className="font-serif text-2xl md:text-3xl text-amber-100 mb-2">
            {displayName}&apos;s Archive
          </h1>
          <p className="text-amber-200/50 text-sm">
            Preserving memories for future generations
          </p>

          {/* Decorative line */}
          <div
            className="w-24 h-px mx-auto mt-6"
            style={{
              background:
                "linear-gradient(90deg, transparent, rgba(212, 165, 116, 0.3), transparent)",
            }}
          />
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Upload Section */}
          <div className="lg:col-span-2 space-y-8">
            <section>
              <h2 className="font-serif text-xl text-amber-100 mb-4 flex items-center gap-3">
                <span
                  className="w-8 h-8 rounded-full flex items-center justify-center text-sm"
                  style={{
                    background: "rgba(139, 115, 85, 0.3)",
                    border: "1px solid rgba(212, 165, 116, 0.2)",
                  }}
                >
                  1
                </span>
                Upload Memories
              </h2>
              <FileUpload
                onFilesSelected={handleFilesSelected}
                disabled={uploadQueue.some(
                  (item) =>
                    item.status === "uploading" || item.status === "processing"
                )}
              />
            </section>

            {uploadQueue.length > 0 && (
              <section>
                <UploadProgress
                  items={uploadQueue}
                  onRemove={handleRemoveFromQueue}
                  onUpload={handleUploadItem}
                  onUpdate={handleUpdateItem}
                />
              </section>
            )}

            {/* Media Assets Grid */}
            {mediaAssets && mediaAssets.length > 0 && (
              <section>
                <h2 className="font-serif text-xl text-amber-100 mb-4">
                  Preserved Memories ({mediaAssets.length})
                </h2>
                <div className="grid sm:grid-cols-2 gap-4">
                  {mediaAssets.map((asset) => (
                    <MediaAssetCard key={asset.id} asset={asset} />
                  ))}
                </div>
              </section>
            )}

            {mediaAssets && mediaAssets.length === 0 && (
              <div
                className="text-center py-16 rounded-lg"
                style={{
                  background: "rgba(30, 20, 10, 0.3)",
                  border: "1px dashed rgba(212, 165, 116, 0.2)",
                }}
              >
                <div
                  className="w-16 h-16 rounded-full mx-auto flex items-center justify-center mb-4"
                  style={{
                    background: "rgba(139, 115, 85, 0.2)",
                  }}
                >
                  <svg
                    className="w-8 h-8 text-amber-200/40"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                    />
                  </svg>
                </div>
                <h3 className="font-serif text-lg text-amber-100 mb-2">
                  No memories uploaded yet
                </h3>
                <p className="text-sm text-amber-200/50">
                  Begin by uploading photographs, letters, or recordings above
                </p>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <aside className="space-y-6">
            <div
              className="rounded-lg p-6"
              style={{
                background: "rgba(30, 20, 10, 0.4)",
                border: "1px solid rgba(212, 165, 116, 0.15)",
              }}
            >
              <h3 className="font-serif text-lg text-amber-100 mb-4">
                Preservation Guide
              </h3>
              <ul className="space-y-4 text-sm">
                <li className="flex items-start gap-3">
                  <span className="text-amber-200/60">I.</span>
                  <span className="text-amber-200/60">
                    Include dates and locations when possible to help weave
                    together stories
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-amber-200/60">II.</span>
                  <span className="text-amber-200/60">
                    Scan letters and documents as images for best preservation
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-amber-200/60">III.</span>
                  <span className="text-amber-200/60">
                    Audio recordings of stories are especially precious
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-amber-200/60">IV.</span>
                  <span className="text-amber-200/60">
                    Group related memories together when uploading
                  </span>
                </li>
              </ul>
            </div>

            <div
              className="rounded-lg p-6"
              style={{
                background: "rgba(60, 40, 20, 0.3)",
                border: "1px solid rgba(212, 165, 116, 0.1)",
              }}
            >
              <h3 className="font-serif text-lg text-amber-100 mb-2">
                Archive Status
              </h3>
              <p className="text-sm text-amber-200/50 mb-4">
                Uploaded files are carefully processed to extract memories and
                stories.
              </p>
              <div className="flex items-center gap-2 text-sm">
                <div className="w-2 h-2 rounded-full bg-amber-500/80 animate-pulse" />
                <span className="text-amber-200/70">System ready</span>
              </div>
            </div>

            <Link
              href="/discover"
              className="block p-6 rounded-lg text-center transition-all hover:scale-[1.02]"
              style={{
                background:
                  "linear-gradient(135deg, rgba(139, 115, 85, 0.3) 0%, rgba(100, 80, 60, 0.3) 100%)",
                border: "1px solid rgba(212, 165, 116, 0.2)",
              }}
            >
              <p className="text-amber-200/60 text-sm mb-2">Ready to connect?</p>
              <p className="font-serif text-amber-100">
                Discover {displayName}&apos;s Stories
              </p>
            </Link>
          </aside>
        </div>
      </main>
    </div>
  );
}
