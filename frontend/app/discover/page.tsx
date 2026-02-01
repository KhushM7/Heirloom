"use client";

import React from "react";
import { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AmbientParticles } from "@/components/ambient-particles";
import { AncestorPresence } from "@/components/ancestor-presence";
import { ImmersiveTranscription } from "@/components/immersive-transcription";
import { MemorySourceDisplay } from "@/components/memory-source-display";
import {
  askQuestionWithVoice,
  cloneVoiceSample,
  createProfile,
  AskResponse,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { DatePicker } from "@/components/date-picker";
import { useProfile } from "@/lib/profile-context";

type SessionState = "intro" | "connecting" | "connected";

export default function DiscoverPage() {
  const { profileId, setProfileId, profileName, setProfileName } = useProfile();
  const [profileNameInput, setProfileNameInput] = useState(profileName);
  const [profileDobInput, setProfileDobInput] = useState("");
  const [sessionState, setSessionState] = useState<SessionState>("intro");
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [currentAnswer, setCurrentAnswer] = useState<AskResponse | null>(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [hasSpoken, setHasSpoken] = useState(false);
  const [connectionPhase, setConnectionPhase] = useState(0);
  const [showQuestionBar, setShowQuestionBar] = useState(true);
  const [profileError, setProfileError] = useState("");
  const [isCreatingProfile, setIsCreatingProfile] = useState(false);
  const [voiceSample, setVoiceSample] = useState<File | null>(null);
  const [voiceError, setVoiceError] = useState("");
  const [isCloningVoice, setIsCloningVoice] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const restoreTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [currentAudio, setCurrentAudio] = useState<{
    data: string;
    mime: string;
  } | null>(null);
  const displayName = profileName || "Ancestor";

  useEffect(() => {
    if (profileId) {
      setSessionState("connected");
    }
  }, [profileId]);

  useEffect(() => {
    setProfileNameInput(profileName);
    setProfileDobInput("");
  }, [profileName]);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profileNameInput.trim()) return;

    setSessionState("connecting");
    setProfileError("");
    setIsCreatingProfile(true);
    setVoiceError("");
    setIsCloningVoice(false);

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
        setSessionState("intro");
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
    } catch (error) {
      setProfileError(
        error instanceof Error ? error.message : "Failed to create profile."
      );
      setSessionState("intro");
      setIsCreatingProfile(false);
      return;
    }

    // Multi-phase connection ritual
    for (let phase = 1; phase <= 4; phase++) {
      setConnectionPhase(phase);
      await new Promise((resolve) => setTimeout(resolve, 1200));
    }

    setSessionState("connected");
    setTimeout(() => inputRef.current?.focus(), 500);
    setIsCreatingProfile(false);
  };

  const fallbackToWebSpeech = useCallback((text: string) => {
    if (!window.speechSynthesis) {
      setIsSpeaking(false);
      setHasSpoken(true);
      return;
    }

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.82;
    utterance.pitch = 0.9;
    utterance.volume = 0.9;

    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(
      (v) =>
        v.name.includes("Natural") ||
        v.name.includes("Premium") ||
        v.lang.startsWith("en")
    );
    if (preferredVoice) utterance.voice = preferredVoice;

    utterance.onend = () => {
      setIsSpeaking(false);
      setHasSpoken(true);
    };

    utterance.onerror = () => {
      setIsSpeaking(false);
      setHasSpoken(true);
    };

    window.speechSynthesis.speak(utterance);
  }, []);

  const playAudio = useCallback(
    async (text: string, audioData?: string, audioMime?: string) => {
      setIsSpeaking(true);
      setHasSpoken(false);

      if (audioData) {
        try {
          const mime = audioMime || "audio/mpeg";
          const audio = new Audio(`data:${mime};base64,${audioData}`);
          audioRef.current = audio;
          audio.onended = () => {
            setIsSpeaking(false);
            setHasSpoken(true);
          };
          audio.onerror = () => {
            audioRef.current = null;
            fallbackToWebSpeech(text);
          };
          await audio.play();
          return;
        } catch {
          audioRef.current = null;
        }
      }

      fallbackToWebSpeech(text);
    },
    [fallbackToWebSpeech]
  );

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isLoading) return;

    const userQuestion = question.trim();
    setQuestion("");
    setIsLoading(true);
    setCurrentAnswer(null);
    setHasSpoken(false);
    setShowQuestionBar(false);

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    window.speechSynthesis?.cancel();
    setIsSpeaking(false);

    try {
      const response = await askQuestionWithVoice(profileId, userQuestion);
      setCurrentAnswer({
        answer_text: response.answer_text,
        source_urls: response.source_urls,
      });
      if (response.audio_base64) {
        setCurrentAudio({
          data: response.audio_base64,
          mime: response.audio_mime_type || "audio/mpeg",
        });
      } else {
        setCurrentAudio(null);
      }
      await playAudio(response.answer_text, response.audio_base64, response.audio_mime_type);
    } catch {
      const fallbackAnswer: AskResponse = {
        answer_text:
          "The memories are stirring, but I cannot quite reach them now. Ask again, and perhaps the connection will be clearer.",
        source_urls: [],
      };
      setCurrentAnswer(fallbackAnswer);
      setCurrentAudio(null);
      await playAudio(fallbackAnswer.answer_text);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReplay = () => {
    if (currentAnswer) {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      window.speechSynthesis?.cancel();
      if (currentAudio) {
        playAudio(currentAnswer.answer_text, currentAudio.data, currentAudio.mime);
      } else {
        playAudio(currentAnswer.answer_text);
      }
    }
  };

  useEffect(() => {
    if (isSpeaking) {
      if (restoreTimerRef.current) {
        clearTimeout(restoreTimerRef.current);
        restoreTimerRef.current = null;
      }
      return;
    }
    if (hasSpoken) {
      restoreTimerRef.current = setTimeout(() => {
        setShowQuestionBar(true);
      }, 3000);
    }
  }, [hasSpoken, isSpeaking]);

  const suggestedQuestions = [
    "What brought you the most joy?",
    "Tell me about your greatest love",
    "What wisdom would you share?",
    "Describe your favorite memory",
  ];

  const connectionMessages = [
    "Lighting the way...",
    "Opening the veil...",
    "Reaching through time...",
    "Connection established...",
  ];

  // Intro / Connection Screen
  if (sessionState !== "connected") {
    return (
      <div className="min-h-screen bg-stone-950 text-amber-100 relative overflow-hidden">
        {/* Deep atmospheric background */}
        <div
          className="absolute inset-0"
          style={{
            background: `
              radial-gradient(ellipse at 50% 30%, rgba(60, 40, 20, 0.5) 0%, transparent 50%),
              radial-gradient(ellipse at 30% 70%, rgba(40, 25, 10, 0.3) 0%, transparent 40%),
              radial-gradient(ellipse at 70% 80%, rgba(50, 30, 15, 0.3) 0%, transparent 40%),
              linear-gradient(to bottom, #0d0908 0%, #0a0705 100%)
            `,
          }}
        />

        {/* Flickering candlelight overlay */}
        <div
          className="absolute inset-0 pointer-events-none animate-pulse"
          style={{
            background: "radial-gradient(ellipse at 50% 40%, rgba(255, 150, 50, 0.03) 0%, transparent 50%)",
            animationDuration: "3s",
          }}
        />

        {/* Vignette */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            boxShadow: "inset 0 0 300px 150px rgba(0, 0, 0, 0.9)",
          }}
        />

        <AmbientParticles intensity={sessionState === "connecting" ? "high" : "low"} />

        {/* Back button */}
        <div className="absolute top-6 left-6 z-20">
          <Link
            href="/"
            className="flex items-center gap-2 text-amber-200/40 hover:text-amber-200/70 transition-colors duration-500"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            <span className="text-sm font-serif">Return</span>
          </Link>
        </div>

        <main className="relative z-10 min-h-screen flex flex-col items-center justify-center px-6">
          {sessionState === "intro" ? (
            <div className="max-w-lg w-full text-center">
              {/* Decorative candle icon */}
              <div className="mb-10 flex justify-center">
                <div className="relative">
                  <svg width="40" height="60" viewBox="0 0 40 60" className="text-amber-200/40">
                    <rect x="15" y="25" width="10" height="35" rx="1" fill="currentColor" opacity="0.6" />
                    <ellipse cx="20" cy="25" rx="6" ry="3" fill="currentColor" opacity="0.4" />
                    <path
                      d="M20 5 Q25 15, 20 22 Q15 15, 20 5"
                      fill="rgba(255, 200, 100, 0.8)"
                      className="animate-pulse"
                      style={{ animationDuration: "1.5s" }}
                    />
                    <ellipse
                      cx="20"
                      cy="14"
                      rx="8"
                      ry="12"
                      fill="url(#candleGlow)"
                      className="animate-pulse"
                      style={{ animationDuration: "2s" }}
                    />
                    <defs>
                      <radialGradient id="candleGlow">
                        <stop offset="0%" stopColor="rgba(255, 180, 80, 0.4)" />
                        <stop offset="100%" stopColor="rgba(255, 150, 50, 0)" />
                      </radialGradient>
                    </defs>
                  </svg>
                </div>
              </div>

              <h1 className="font-serif text-4xl md:text-5xl text-amber-100 mb-6 tracking-wide">
                The Veil Between Worlds
              </h1>

              <p className="text-amber-200/50 text-lg mb-12 leading-relaxed font-serif">
                In this sacred space, the boundary between past and present grows thin. 
                Speak a name, and the spirits of memory shall answer.
              </p>

              <form onSubmit={handleConnect} className="space-y-8">
                <div className="relative group">
                  {/* Glowing border effect */}
                  <div className="absolute -inset-1 bg-gradient-to-r from-amber-900/0 via-amber-600/20 to-amber-900/0 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity duration-700 blur-sm" />
                  
                  <input
                    type="text"
                    placeholder="Whisper their name..."
                    value={profileNameInput}
                    onChange={(e) => setProfileNameInput(e.target.value)}
                    className={cn(
                      "relative w-full bg-stone-900/30 border border-amber-200/15 text-amber-100",
                      "placeholder:text-amber-200/25 h-16 text-center text-xl font-serif",
                      "focus:border-amber-200/40 focus:outline-none focus:ring-2 focus:ring-amber-200/10",
                      "rounded-lg transition-all duration-500"
                    )}
                    required
                  />
                </div>

                <DatePicker
                  value={profileDobInput}
                  onChange={setProfileDobInput}
                  placeholder="Date of birth (optional)"
                />

                <div className="space-y-2">
                  <label className="block text-xs uppercase tracking-[0.2em] text-amber-200/40 font-serif">
                    Voice Sample (optional)
                  </label>
                  <div className="relative">
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
                  </div>
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
                    !profileNameInput.trim() || isCreatingProfile || isCloningVoice
                  }
                  className={cn(
                    "w-full h-14 text-lg font-serif tracking-wide rounded-lg",
                    "bg-gradient-to-r from-amber-900/60 via-amber-800/70 to-amber-900/60",
                    "hover:from-amber-800/70 hover:via-amber-700/80 hover:to-amber-800/70",
                    "border border-amber-200/20 text-amber-100",
                    "transition-all duration-500 disabled:opacity-30",
                    "shadow-lg shadow-amber-900/20"
                  )}
                >
                  {isCloningVoice
                    ? "Capturing Voice..."
                    : isCreatingProfile
                    ? "Connecting..."
                    : "Light the Candle"}
                </Button>
                {profileError && (
                  <p className="text-xs text-red-300/80">{profileError}</p>
                )}
              </form>

              {/* Bottom decorative line */}
              <div className="mt-16 flex justify-center">
                <div
                  className="w-48 h-px"
                  style={{
                    background: "linear-gradient(90deg, transparent, rgba(212, 165, 116, 0.3), transparent)",
                  }}
                />
              </div>
            </div>
          ) : (
            // Connection ritual animation
            <div className="text-center max-w-md">
              {/* Central ritual circle */}
              <div className="relative w-64 h-64 mx-auto mb-12">
                {/* Outer rotating ring */}
                <div
                  className="absolute inset-0 rounded-full border border-amber-200/20 animate-spin"
                  style={{ animationDuration: "20s" }}
                />
                
                {/* Pulsing rings */}
                {[0, 1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className={cn(
                      "absolute rounded-full transition-all duration-1000",
                      connectionPhase > i ? "opacity-100" : "opacity-0"
                    )}
                    style={{
                      inset: `${i * 15}px`,
                      background: `radial-gradient(circle, rgba(255, 200, 150, ${0.15 - i * 0.03}) 0%, transparent 70%)`,
                      animation: connectionPhase > i ? "pulse 2s ease-in-out infinite" : "none",
                      animationDelay: `${i * 0.3}s`,
                    }}
                  />
                ))}

                {/* Center spirit emergence */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <div
                    className={cn(
                      "w-24 h-24 rounded-full transition-all duration-1000",
                      connectionPhase >= 3 ? "scale-100 opacity-100" : "scale-50 opacity-0"
                    )}
                    style={{
                      background: "radial-gradient(circle, rgba(255, 220, 180, 0.4) 0%, rgba(255, 180, 120, 0.1) 50%, transparent 70%)",
                      boxShadow: "0 0 60px rgba(255, 200, 150, 0.3)",
                    }}
                  />
                </div>

                {/* Corner runes/symbols */}
                {[0, 90, 180, 270].map((angle, i) => (
                  <div
                    key={angle}
                    className={cn(
                      "absolute w-4 h-4 transition-all duration-700",
                      connectionPhase > i ? "opacity-60" : "opacity-0"
                    )}
                    style={{
                      top: `${50 + 45 * Math.sin((angle * Math.PI) / 180)}%`,
                      left: `${50 + 45 * Math.cos((angle * Math.PI) / 180)}%`,
                      transform: "translate(-50%, -50%)",
                    }}
                  >
                    <svg viewBox="0 0 20 20" className="text-amber-200/60">
                      <circle cx="10" cy="10" r="3" fill="currentColor" />
                    </svg>
                  </div>
                ))}
              </div>

              {/* Connection message */}
              <p className="font-serif text-2xl text-amber-200/80 mb-3">
                {connectionMessages[connectionPhase - 1] || connectionMessages[0]}
              </p>
              <p className="text-amber-200/40 text-sm font-serif">
                Summoning the spirit of {displayName}
              </p>

              {/* Progress indicators */}
              <div className="flex justify-center gap-3 mt-8">
                {[1, 2, 3, 4].map((phase) => (
                  <div
                    key={phase}
                    className={cn(
                      "w-2 h-2 rounded-full transition-all duration-500",
                      connectionPhase >= phase
                        ? "bg-amber-200/80 scale-110"
                        : "bg-amber-200/20"
                    )}
                    style={{
                      boxShadow: connectionPhase >= phase
                        ? "0 0 10px rgba(255, 200, 150, 0.5)"
                        : "none",
                    }}
                  />
                ))}
              </div>
            </div>
          )}
        </main>
      </div>
    );
  }

  // Connected / Séance Screen
  return (
    <div className="min-h-screen bg-stone-950 text-amber-100 relative overflow-hidden">
      {/* Layered atmospheric background */}
      <div
        className="absolute inset-0"
        style={{
          background: `
            radial-gradient(ellipse at 50% 15%, rgba(80, 55, 25, 0.4) 0%, transparent 45%),
            radial-gradient(ellipse at 20% 80%, rgba(50, 30, 15, 0.2) 0%, transparent 35%),
            radial-gradient(ellipse at 80% 70%, rgba(45, 28, 12, 0.2) 0%, transparent 35%),
            linear-gradient(to bottom, #0d0908 0%, #080604 100%)
          `,
        }}
      />

      {/* Warm glow from presence area */}
      <div
        className={cn(
          "absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] pointer-events-none transition-opacity duration-1000",
          isSpeaking ? "opacity-100" : "opacity-60"
        )}
        style={{
          background: "radial-gradient(ellipse at 50% 30%, rgba(255, 180, 100, 0.08) 0%, transparent 60%)",
        }}
      />

      {/* Heavy vignette for focus */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          boxShadow: "inset 0 0 300px 150px rgba(0, 0, 0, 0.9)",
        }}
      />

      <AmbientParticles intensity={isSpeaking ? "high" : "medium"} />

      {/* Subtle back button */}
      <div className="absolute top-6 left-6 z-20">
        <Link
          href="/"
          className="flex items-center gap-2 text-amber-200/30 hover:text-amber-200/60 transition-colors duration-500"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          <span className="text-xs font-serif">Depart</span>
        </Link>
      </div>

      <main className="relative z-10 min-h-screen flex flex-col">
        {/* Ancestor presence - central focus */}
        <div className="flex-shrink-0 pt-8 pb-4 flex justify-center">
          <AncestorPresence
            name={displayName}
            isSpeaking={isSpeaking}
            isThinking={isLoading}
          />
        </div>

        {/* Response area - flows naturally */}
        <div className="flex-1 flex flex-col items-center justify-center px-4 py-6">
          {currentAnswer ? (
            <div className="w-full max-w-2xl space-y-4">
              {!isSpeaking && hasSpoken && currentAnswer.source_urls && currentAnswer.source_urls.length > 0 && (
                <MemorySourceDisplay sources={currentAnswer.source_urls} />
              )}

              <ImmersiveTranscription
                text={currentAnswer.answer_text}
                isPlaying={isSpeaking}
              />

              {/* Replay and sources - appear after speaking */}
              {!isSpeaking && hasSpoken && (
                <div className="space-y-8 animate-in fade-in duration-1000">
                  <div className="flex justify-center">
                    <button
                      type="button"
                      onClick={handleReplay}
                      className="flex items-center gap-2 px-5 py-2.5 rounded-full text-sm text-amber-200/50 hover:text-amber-200/80 border border-amber-200/10 hover:border-amber-200/30 bg-stone-900/30 hover:bg-stone-900/50 transition-all duration-300"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="font-serif">Hear again</span>
                    </button>
                  </div>

                </div>
              )}
            </div>
          ) : !isLoading ? (
            // Waiting state
            <div className="text-center max-w-lg px-4">
              <p className="text-amber-200/30 text-xl font-serif leading-relaxed">
                The spirit of {displayName} awaits your questions...
              </p>
            </div>
          ) : (
            // Loading state
            <div className="text-center">
              <div className="flex justify-center mb-6">
                <div className="relative w-16 h-16">
                  <div className="absolute inset-0 rounded-full border border-amber-200/30 animate-ping" style={{ animationDuration: "1.5s" }} />
                  <div className="absolute inset-2 rounded-full border border-amber-200/20 animate-ping" style={{ animationDuration: "1.5s", animationDelay: "0.3s" }} />
                  <div className="absolute inset-4 rounded-full bg-amber-200/10 animate-pulse" />
                </div>
              </div>
              <p className="text-amber-200/50 font-serif text-lg">
                Searching the memories...
              </p>
            </div>
          )}
        </div>

        {/* Input area - grounded at bottom */}
        <div
          className={cn(
            "flex-shrink-0 pb-10 px-6 transition-all duration-700",
            showQuestionBar ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6 pointer-events-none"
          )}
        >
          <div className="max-w-xl mx-auto">
            {/* Decorative separator */}
            <div className="flex items-center justify-center gap-4 mb-6">
              <div className="flex-1 h-px bg-gradient-to-r from-transparent to-amber-200/20" />
              <svg width="20" height="20" viewBox="0 0 20 20" className="text-amber-200/30">
                <circle cx="10" cy="10" r="2" fill="currentColor" />
              </svg>
              <div className="flex-1 h-px bg-gradient-to-l from-transparent to-amber-200/20" />
            </div>

            <form onSubmit={handleAsk} className="relative">
              <div className="flex gap-4">
                <div className="flex-1 relative">
                  <input
                    ref={inputRef}
                    type="text"
                    placeholder="Ask your question..."
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    disabled={isLoading || isSpeaking}
                    className={cn(
                      "w-full bg-stone-900/40 border border-amber-200/15 text-amber-100",
                      "placeholder:text-amber-200/25 h-14 px-6 text-lg font-serif rounded-full",
                      "focus:border-amber-200/40 focus:outline-none focus:ring-2 focus:ring-amber-200/10",
                      "disabled:opacity-40 transition-all duration-300"
                    )}
                  />
                </div>

                <Button
                  type="submit"
                  disabled={!question.trim() || isLoading || isSpeaking}
                  className={cn(
                    "h-14 w-14 p-0 rounded-full",
                    "bg-gradient-to-br from-amber-800/70 to-amber-900/80",
                    "hover:from-amber-700/80 hover:to-amber-800/90",
                    "border border-amber-200/20 text-amber-100",
                    "disabled:opacity-20 transition-all duration-300",
                    "shadow-lg shadow-amber-900/30"
                  )}
                >
                  {isLoading ? (
                    <div className="w-5 h-5 border-2 border-amber-200/30 border-t-amber-200/80 rounded-full animate-spin" />
                  ) : (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
                  )}
                </Button>
              </div>
            </form>

            <div className={cn("mt-6 transition-opacity duration-700", showQuestionBar ? "opacity-100" : "opacity-0")}>
              <div className="flex flex-wrap justify-center gap-3">
                {suggestedQuestions.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => setQuestion(q)}
                    className={cn(
                      "px-5 py-2.5 text-sm rounded-full transition-all duration-500 font-serif",
                      "border border-amber-200/15 text-amber-200/40 bg-stone-900/20",
                      "hover:border-amber-200/40 hover:text-amber-200/70 hover:bg-stone-900/40",
                      "hover:shadow-lg hover:shadow-amber-900/20"
                    )}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>

            <p className="text-center text-xs text-amber-200/20 mt-5 font-serif tracking-wide">
              Speak from your heart. The spirit hears all.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
