"use client";

import { useEffect, useRef, useState } from "react";
import { AvatarPicker } from "@/components/AvatarPicker";
import { VoiceSelector } from "@/components/VoiceSelector";
import { VideoResult } from "@/components/VideoResult";
import { AVATARS, DEFAULT_AVATAR_ID } from "@/lib/avatars";
import { VOICES, DEFAULT_VOICE_ID } from "@/lib/voices";
import { MAX_TEXT_LENGTH } from "@/lib/validation";

const POLL_INTERVAL_MS = 3000;
const POLL_TIMEOUT_MS = 3 * 60 * 1000;

type GenerationState =
  | { phase: "idle" }
  | { phase: "submitting" }
  | { phase: "polling"; jobId: string }
  | { phase: "done"; videoUrl: string }
  | { phase: "error"; message: string };

export default function Home() {
  const [text, setText] = useState("");
  const [avatarId, setAvatarId] = useState(DEFAULT_AVATAR_ID);
  const [voiceId, setVoiceId] = useState(DEFAULT_VOICE_ID);
  const [state, setState] = useState<GenerationState>({ phase: "idle" });

  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollDeadline = useRef<number>(0);

  useEffect(() => {
    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
    };
  }, []);

  function stopPolling() {
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
  }

  function startPolling(jobId: string) {
    stopPolling();
    pollDeadline.current = Date.now() + POLL_TIMEOUT_MS;

    pollTimer.current = setInterval(async () => {
      if (Date.now() > pollDeadline.current) {
        stopPolling();
        setState({ phase: "error", message: "Video generation is taking longer than expected. Please try again." });
        return;
      }

      try {
        const response = await fetch(`/api/status/${encodeURIComponent(jobId)}`);
        const data = await response.json();

        if (!response.ok) {
          stopPolling();
          setState({ phase: "error", message: data.error || "Something went wrong while checking video status." });
          return;
        }

        if (data.status === "done" && data.videoUrl) {
          stopPolling();
          setState({ phase: "done", videoUrl: data.videoUrl });
        } else if (data.status === "error") {
          stopPolling();
          setState({ phase: "error", message: data.error || "Video generation failed." });
        }
        // "pending" / "processing" -> keep polling
      } catch {
        stopPolling();
        setState({ phase: "error", message: "Lost connection while checking video status. Please try again." });
      }
    }, POLL_INTERVAL_MS);
  }

  async function handleGenerate() {
    setState({ phase: "submitting" });
    try {
      const response = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, avatarId, voiceId }),
      });
      const data = await response.json();

      if (!response.ok) {
        setState({ phase: "error", message: data.error || "Something went wrong while starting video generation." });
        return;
      }

      setState({ phase: "polling", jobId: data.jobId });
      startPolling(data.jobId);
    } catch {
      setState({ phase: "error", message: "Could not reach the server. Please check your connection and try again." });
    }
  }

  const isBusy = state.phase === "submitting" || state.phase === "polling";
  const trimmedLength = text.trim().length;
  const canGenerate = !isBusy && trimmedLength > 0 && text.length <= MAX_TEXT_LENGTH;

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 px-4 py-10">
      <header>
        <h1 className="text-2xl font-semibold">Avatar Video Generator</h1>
        <p className="mt-1 text-sm text-slate-600">Type some text, pick an avatar and voice, and generate a talking video.</p>
      </header>

      <section className="flex flex-col gap-2">
        <label htmlFor="script" className="text-sm font-medium">
          Text
        </label>
        <textarea
          id="script"
          value={text}
          onChange={(event) => setText(event.target.value)}
          disabled={isBusy}
          rows={6}
          maxLength={MAX_TEXT_LENGTH}
          placeholder="Type what you'd like the avatar to say..."
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50"
        />
        <span className={`self-end text-xs ${text.length > MAX_TEXT_LENGTH ? "text-red-600" : "text-slate-500"}`}>
          {text.length} / {MAX_TEXT_LENGTH}
        </span>
      </section>

      <section className="flex flex-col gap-2">
        <span className="text-sm font-medium">Avatar</span>
        <AvatarPicker avatars={AVATARS} selectedId={avatarId} onSelect={setAvatarId} disabled={isBusy} />
      </section>

      <section className="flex flex-col gap-2">
        <label htmlFor="voice" className="text-sm font-medium">
          Voice / language
        </label>
        <VoiceSelector voices={VOICES} selectedId={voiceId} onSelect={setVoiceId} disabled={isBusy} />
      </section>

      <button
        type="button"
        onClick={handleGenerate}
        disabled={!canGenerate}
        className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isBusy && (
          <span
            className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
            aria-hidden="true"
          />
        )}
        {state.phase === "submitting"
          ? "Starting generation..."
          : state.phase === "polling"
            ? "Generating video..."
            : "Generate Video"}
      </button>

      {state.phase === "error" && (
        <div role="alert" className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {state.message}
        </div>
      )}

      {state.phase === "polling" && (
        <p className="text-sm text-slate-600">This usually takes 10-60 seconds. Feel free to wait, this page will update automatically.</p>
      )}

      {state.phase === "done" && <VideoResult videoUrl={state.videoUrl} />}
    </main>
  );
}
