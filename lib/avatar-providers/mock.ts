import { AvatarProvider, CreateVideoParams, CreateVideoResult, JobStatusResult } from "./types";

// Simulates a provider without calling any external API or spending quota.
// Useful for local development and for testing the frontend's polling and
// error-handling states. Enable with AVATAR_PROVIDER=mock.
const SAMPLE_VIDEO_URL =
  "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4";
const PROCESSING_POLLS_BEFORE_DONE = 2;

const jobs = new Map<string, { pollsRemaining: number; shouldFail: boolean }>();
let counter = 0;

export class MockAvatarProvider implements AvatarProvider {
  name = "mock";

  async createVideo(params: CreateVideoParams): Promise<CreateVideoResult> {
    counter += 1;
    const jobId = `mock_${counter}`;
    jobs.set(jobId, {
      pollsRemaining: PROCESSING_POLLS_BEFORE_DONE,
      shouldFail: params.text.toLowerCase().includes("fail"),
    });
    return { jobId };
  }

  async getJobStatus(jobId: string): Promise<JobStatusResult> {
    const job = jobs.get(jobId);
    if (!job) {
      return { status: "error", error: "Unknown job id." };
    }

    if (job.pollsRemaining > 0) {
      job.pollsRemaining -= 1;
      return { status: job.pollsRemaining === PROCESSING_POLLS_BEFORE_DONE - 1 ? "pending" : "processing" };
    }

    if (job.shouldFail) {
      return { status: "error", error: "Mock provider: generation failed on purpose (text contained 'fail')." };
    }

    return { status: "done", videoUrl: SAMPLE_VIDEO_URL };
  }
}
