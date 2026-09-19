import { NextResponse } from "next/server";
import { getAvatarProvider, ProviderError } from "@/lib/avatar-providers";
import { getAvatarById } from "@/lib/avatars";
import { getVoiceById } from "@/lib/voices";
import { checkRateLimit, getClientKey } from "@/lib/rate-limit";
import { MAX_TEXT_LENGTH, MIN_TEXT_LENGTH } from "@/lib/validation";

export const dynamic = "force-dynamic";
export const fetchCache = "force-no-store";

export async function POST(request: Request) {
  const rateLimit = checkRateLimit(getClientKey(request));
  if (!rateLimit.allowed) {
    const retryAfterSeconds = Math.max(1, Math.ceil((rateLimit.resetAt - Date.now()) / 1000));
    return NextResponse.json(
      { error: "You've reached the generation limit for now. Please try again later." },
      { status: 429, headers: { "Retry-After": String(retryAfterSeconds) } },
    );
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Request body must be valid JSON." }, { status: 400 });
  }

  const { text, avatarId, voiceId } = (body ?? {}) as {
    text?: unknown;
    avatarId?: unknown;
    voiceId?: unknown;
  };

  if (typeof text !== "string" || text.trim().length < MIN_TEXT_LENGTH) {
    return NextResponse.json({ error: "Please enter some text for the avatar to say." }, { status: 400 });
  }
  if (text.length > MAX_TEXT_LENGTH) {
    return NextResponse.json(
      { error: `Text is too long (${text.length} characters). Please keep it under ${MAX_TEXT_LENGTH} characters.` },
      { status: 400 },
    );
  }

  const avatar = getAvatarById(typeof avatarId === "string" ? avatarId : "");
  if (!avatar) {
    return NextResponse.json({ error: "Please choose a valid avatar." }, { status: 400 });
  }

  const voice = getVoiceById(typeof voiceId === "string" ? voiceId : "");
  if (!voice) {
    return NextResponse.json({ error: "Please choose a valid voice." }, { status: 400 });
  }

  try {
    const provider = getAvatarProvider();
    const result = await provider.createVideo({
      text: text.trim(),
      avatarImageUrl: avatar.imageUrl,
      voiceId: voice.id,
      voiceProvider: voice.provider,
    });
    return NextResponse.json({ jobId: result.jobId });
  } catch (error) {
    if (error instanceof ProviderError) {
      if (error.statusCode >= 500) {
        console.error("Avatar provider error:", error.message);
      }
      return NextResponse.json({ error: error.message }, { status: error.statusCode });
    }
    console.error("Unexpected error creating video:", error);
    return NextResponse.json({ error: "Something went wrong while starting video generation." }, { status: 500 });
  }
}
