"use client";

import React from "react";
import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AmbientParticles } from "@/components/ambient-particles";

export default function HomePage() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className="min-h-screen bg-stone-950 text-amber-100 relative overflow-hidden">
      {/* Ambient background */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at 50% 0%, rgba(60, 40, 20, 0.4) 0%, rgba(15, 10, 5, 1) 70%)",
        }}
      />

      {/* Vignette overlay */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          boxShadow: "inset 0 0 200px 80px rgba(0, 0, 0, 0.7)",
        }}
      />

      {mounted && <AmbientParticles />}

      {/* Header */}
      <header className="relative z-20 py-6 px-6">
        <nav className="max-w-6xl mx-auto flex items-center justify-between">
          <Link
            href="/"
            className="font-serif text-xl text-amber-100 flex items-center gap-3"
          >
            <Image
              src="/logo.svg"
              alt="Heirloom logo"
              width={100}
              height={100}
              className="h-25 w-25"
              priority
            />
          </Link>
          <div className="flex items-center gap-6">
            <Link
              href="/preserve"
              className="text-sm text-amber-200/60 hover:text-amber-200 transition-colors"
            >
              Preserve
            </Link>
            <Link
              href="/discover"
              className="text-sm text-amber-200/60 hover:text-amber-200 transition-colors"
            >
              Discover
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="relative z-10 min-h-[80vh] flex items-center justify-center px-6">
        <div
          className={`max-w-3xl mx-auto text-center transition-all duration-1000 ${
            mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
          }`}
        >
          {/* Decorative element */}
          <div className="mb-8 flex justify-center">
            <div
              className="w-24 h-px"
              style={{
                background:
                  "linear-gradient(90deg, transparent, rgba(212, 165, 116, 0.5), transparent)",
              }}
            />
          </div>

          <h1 className="font-serif text-4xl md:text-6xl lg:text-7xl text-amber-100 leading-tight text-balance">
            Speak With Those
            <span className="block mt-2 text-amber-200/80">Who Came Before</span>
          </h1>

          <p className="mt-8 text-lg md:text-xl text-amber-200/60 leading-relaxed max-w-2xl mx-auto text-pretty">
            Preserve photographs, letters, and recordings. Then ask questions
            and hear your ancestors&apos; stories come alive through their own
            preserved memories.
          </p>

          <div className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/preserve">
              <Button
                size="lg"
                className="px-8 h-14 text-lg font-serif bg-gradient-to-r from-amber-900/80 to-amber-800/80 hover:from-amber-800/80 hover:to-amber-700/80 border border-amber-200/20 text-amber-100"
              >
                Begin Preserving
              </Button>
            </Link>
            <Link href="/discover">
              <Button
                variant="outline"
                size="lg"
                className="px-8 h-14 text-lg font-serif bg-transparent border-amber-200/30 text-amber-200/80 hover:bg-amber-200/10 hover:text-amber-100 hover:border-amber-200/50"
              >
                Connect With the Past
              </Button>
            </Link>
          </div>

          {/* Decorative element */}
          <div className="mt-16 flex justify-center">
            <div
              className="w-16 h-px"
              style={{
                background:
                  "linear-gradient(90deg, transparent, rgba(212, 165, 116, 0.3), transparent)",
              }}
            />
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="relative z-10 py-24 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <p className="text-xs text-amber-200/40 uppercase tracking-[0.3em] mb-4">
              How It Works
            </p>
            <h2 className="font-serif text-3xl md:text-4xl text-amber-100">
              Three Steps to Connection
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard
              number="I"
              title="Preserve"
              description="Upload cherished photographs, handwritten letters, voice recordings, and documents from your family's history."
              icon={
                <svg
                  className="w-6 h-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                  />
                </svg>
              }
            />
            <FeatureCard
              number="II"
              title="Process"
              description="Our system carefully analyzes your uploads, extracting meaningful memories, stories, and connections."
              icon={
                <svg
                  className="w-6 h-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                  />
                </svg>
              }
            />
            <FeatureCard
              number="III"
              title="Connect"
              description="Ask questions and receive spoken answers, as if your ancestor were sharing their stories directly with you."
              icon={
                <svg
                  className="w-6 h-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
              }
            />
          </div>
        </div>
      </section>

      {/* Quote Section */}
      <section className="relative z-10 py-24 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <div
            className="w-12 h-px mx-auto mb-8"
            style={{
              background:
                "linear-gradient(90deg, transparent, rgba(212, 165, 116, 0.4), transparent)",
            }}
          />

          <blockquote className="font-serif text-2xl md:text-3xl text-amber-100/80 italic leading-relaxed">
            &ldquo;We do not inherit the stories of our ancestors. We borrow
            them from our children.&rdquo;
          </blockquote>

          <div
            className="w-12 h-px mx-auto mt-8"
            style={{
              background:
                "linear-gradient(90deg, transparent, rgba(212, 165, 116, 0.4), transparent)",
            }}
          />
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative z-10 py-24 px-6">
        <div
          className="max-w-4xl mx-auto text-center p-12 rounded-lg"
          style={{
            background:
              "linear-gradient(180deg, rgba(60, 40, 20, 0.3) 0%, rgba(40, 25, 10, 0.3) 100%)",
            border: "1px solid rgba(212, 165, 116, 0.15)",
          }}
        >
          <h2 className="font-serif text-3xl md:text-4xl text-amber-100">
            Begin Your Family&apos;s Archive
          </h2>
          <p className="mt-4 text-amber-200/60 max-w-xl mx-auto">
            Every photograph holds a story. Every letter carries a voice. Start
            preserving the memories that matter most.
          </p>
          <Link href="/preserve">
            <Button
              size="lg"
              className="mt-8 px-10 h-14 text-lg font-serif bg-gradient-to-r from-amber-900/80 to-amber-800/80 hover:from-amber-800/80 hover:to-amber-700/80 border border-amber-200/20 text-amber-100"
            >
              Start Preserving
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 py-8 px-6 border-t border-amber-200/10">
        <div className="max-w-6xl mx-auto text-center">
          <p className="text-sm text-amber-200/40">
            Heirloom — Preserving memories, connecting generations
          </p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({
  number,
  title,
  description,
  icon,
}: {
  number: string;
  title: string;
  description: string;
  icon: React.ReactNode;
}) {
  return (
    <div
      className="relative p-8 rounded-lg transition-all duration-300 hover:bg-amber-200/5 group"
      style={{
        background: "rgba(30, 20, 10, 0.3)",
        border: "1px solid rgba(212, 165, 116, 0.1)",
      }}
    >
      <div className="absolute top-4 right-4 font-serif text-4xl font-bold text-amber-200/10 group-hover:text-amber-200/20 transition-colors">
        {number}
      </div>
      <div className="w-12 h-12 rounded-full bg-amber-200/10 flex items-center justify-center text-amber-200/70 mb-6 group-hover:bg-amber-200/15 group-hover:text-amber-200 transition-all">
        {icon}
      </div>
      <h3 className="font-serif text-xl text-amber-100 mb-3">{title}</h3>
      <p className="text-amber-200/50 text-sm leading-relaxed">{description}</p>
    </div>
  );
}
