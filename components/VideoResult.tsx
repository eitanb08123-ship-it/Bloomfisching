"use client";

interface VideoResultProps {
  videoUrl: string;
}

export function VideoResult({ videoUrl }: VideoResultProps) {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4">
      {/* eslint-disable-next-line jsx-a11y/media-has-caption -- generated speech has no caption track */}
      <video src={videoUrl} controls className="w-full rounded-md bg-black" />
      <a
        href={videoUrl}
        download
        className="inline-flex w-fit items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
      >
        Download video
      </a>
    </div>
  );
}
