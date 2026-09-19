export interface CreateVideoParams {
  text: string;
  avatarImageUrl: string;
  voiceId: string;
  voiceProvider: string;
}

export interface CreateVideoResult {
  jobId: string;
}

export type JobStatus = "pending" | "processing" | "done" | "error";

export interface JobStatusResult {
  status: JobStatus;
  videoUrl?: string;
  error?: string;
}

export class ProviderError extends Error {
  /** HTTP status code the API route should respond with. */
  statusCode: number;

  constructor(message: string, statusCode = 502) {
    super(message);
    this.name = "ProviderError";
    this.statusCode = statusCode;
  }
}

export interface AvatarProvider {
  name: string;
  createVideo(params: CreateVideoParams): Promise<CreateVideoResult>;
  getJobStatus(jobId: string): Promise<JobStatusResult>;
}
