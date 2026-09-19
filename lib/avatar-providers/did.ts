import {
  AvatarProvider,
  CreateVideoParams,
  CreateVideoResult,
  JobStatusResult,
  ProviderError,
} from "./types";

// D-ID API keys are copied from the dashboard as a raw "username:password"
// string; Basic auth requires base64-encoding that pair ourselves.
// https://docs.d-id.com/reference/basic-authentication
function buildAuthHeader(apiKey: string): string {
  return `Basic ${Buffer.from(apiKey, "utf-8").toString("base64")}`;
}

interface DidCreateTalkResponse {
  id: string;
}

interface DidGetTalkResponse {
  id: string;
  status: "created" | "started" | "done" | "error" | "rejected";
  result_url?: string;
  error?: { description?: string; kind?: string } | string;
}

function throwForFailedResponse(status: number, body: string): never {
  const message = describeHttpError(status, body);
  // 401/403 mean the key itself is the problem - surface it as a server
  // misconfiguration (with the provider's own error text logged) rather
  // than a generic upstream failure.
  throw new ProviderError(message, status === 401 || status === 403 ? 500 : 502);
}

function describeHttpError(status: number, body: string): string {
  if (status === 401 || status === 403) {
    return `The avatar-video provider rejected our API key (HTTP ${status}). Check the server's DID_API_KEY configuration. Provider response: ${body || "(empty)"}`;
  }
  if (status === 429) {
    return "The avatar-video provider's rate limit or free-tier quota has been reached. Please try again later.";
  }
  if (status === 400) {
    return `The avatar-video provider rejected the request: ${body || "invalid input."}`;
  }
  return `The avatar-video provider is currently unavailable (HTTP ${status}). Please try again in a moment. Provider response: ${body || "(empty)"}`;
}

export class DidAvatarProvider implements AvatarProvider {
  name = "did";

  private apiKey: string;
  private baseUrl: string;

  constructor(apiKey: string, baseUrl = "https://api.d-id.com") {
    if (!apiKey) {
      throw new ProviderError(
        "Avatar-video generation is not configured on the server (missing DID_API_KEY).",
        500,
      );
    }
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
  }

  async createVideo(params: CreateVideoParams): Promise<CreateVideoResult> {
    const response = await fetch(`${this.baseUrl}/talks`, {
      method: "POST",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        Authorization: buildAuthHeader(this.apiKey),
      },
      body: JSON.stringify({
        source_url: params.avatarImageUrl,
        script: {
          type: "text",
          input: params.text,
          provider: {
            type: params.voiceProvider,
            voice_id: params.voiceId,
          },
        },
      }),
    });

    if (!response.ok) {
      throwForFailedResponse(response.status, await response.text());
    }

    const data = (await response.json()) as DidCreateTalkResponse;
    return { jobId: data.id };
  }

  async getJobStatus(jobId: string): Promise<JobStatusResult> {
    const response = await fetch(`${this.baseUrl}/talks/${encodeURIComponent(jobId)}`, {
      method: "GET",
      cache: "no-store",
      headers: {
        Authorization: buildAuthHeader(this.apiKey),
      },
    });

    if (!response.ok) {
      throwForFailedResponse(response.status, await response.text());
    }

    const data = (await response.json()) as DidGetTalkResponse;

    switch (data.status) {
      case "created":
        return { status: "pending" };
      case "started":
        return { status: "processing" };
      case "done":
        return { status: "done", videoUrl: data.result_url };
      case "error":
      case "rejected": {
        const message =
          typeof data.error === "string"
            ? data.error
            : data.error?.description || "Video generation failed.";
        return { status: "error", error: message };
      }
      default:
        return { status: "processing" };
    }
  }
}
