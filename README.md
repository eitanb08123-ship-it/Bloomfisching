# Avatar Video Generator

Type some text, pick an avatar and a voice, and get back a video of that avatar speaking your text.

Built with Next.js (App Router). The frontend and backend live in a single project: the browser
never talks to the video-generation provider directly, only to this app's own API routes, which
hold the provider API key server-side.

## How it works

1. You type text (a few paragraphs max), pick a preset avatar and a voice/language.
2. `POST /api/generate` validates the input, applies a per-IP rate limit, and asks the configured
   provider to start generating a video. This returns a `jobId` immediately — generation itself is
   async and takes roughly 10-60 seconds.
3. The frontend polls `GET /api/status/:jobId` every few seconds until the provider reports the
   video is `done` (or `error`).
4. Once done, the page shows a video player and a download button.

## Provider adapter

`lib/avatar-providers/` defines a small `AvatarProvider` interface (`createVideo`, `getJobStatus`)
so the rest of the app never talks to a specific vendor's API directly:

- `did.ts` — the real implementation, calling [D-ID](https://www.d-id.com/api)'s REST API
  (`POST /talks` to start a job, `GET /talks/:id` to poll it).
- `mock.ts` — a local simulator with no external calls, useful for developing/testing the UI
  without spending D-ID's free-tier quota. Include the word "fail" in the input text to make a
  mock job end in an error, to exercise the error-handling UI.

`lib/avatar-providers/index.ts` picks one of these based on the `AVATAR_PROVIDER` env var. Adding a
new provider (e.g. HeyGen, Synthesia) means writing one more class that implements
`AvatarProvider` and adding a case there — nothing else in the app changes.

## Setup

```bash
npm install
cp .env.example .env.local
```

Then edit `.env.local`:

- `DID_API_KEY` — get a free-tier key from the [D-ID Studio](https://studio.d-id.com/account-settings).
  It's given to you already as `username:password`; paste it in exactly like that, the server
  base64-encodes it for Basic auth on each request. This key is read only on the server
  (`process.env.DID_API_KEY` inside route handlers) — it is never sent to or bundled into the
  browser.
- `AVATAR_PROVIDER` — `did` (default) for real generation, or `mock` to develop without an API key.
- `RATE_LIMIT_MAX` / `RATE_LIMIT_WINDOW_MS` — how many generations a single IP may start per
  time window (defaults: 5 per hour). This is a simple in-memory limiter meant to stop a public
  deployment's free-tier quota from being burned instantly; it resets on server restart and isn't
  shared across multiple server instances, so swap in a shared store (e.g. Redis) before deploying
  behind more than one instance.

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Error handling

The app surfaces clear messages for the failure cases called out in the spec: empty/too-long text
(validated client- and server-side against `MAX_TEXT_LENGTH`), an invalid avatar/voice choice, the
provider's rate limit or quota being exceeded (HTTP 429), an invalid/misconfigured API key, and the
provider itself reporting the generation failed. The frontend also times out and shows an error if
polling runs past 3 minutes without a result.

## Known limitations / next steps

- Pinned to Next.js 14.2.x (latest patch on that line) to keep the App Router's synchronous route
  params API. `npm audit` still flags some CVEs that are only fixed in Next.js 15/16 or that live in
  Next's own bundled dependencies; none of the affected features (Server Actions, `next/image`
  optimization, Pages Router i18n) are used by this app, but a major-version upgrade is worth doing
  before any public/production deployment.
- The rate limiter is per-instance and in-memory (see above) — fine for a single small deployment,
  not for a multi-instance one.
- Only two preset avatars and four preset voices (English + Hebrew) are wired up so far; add more
  to `lib/avatars.ts` / `lib/voices.ts` to expand the gallery/selector.
