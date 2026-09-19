import { NextResponse } from "next/server";
import { getAvatarProvider, ProviderError } from "@/lib/avatar-providers";

export async function GET(_request: Request, { params }: { params: { jobId: string } }) {
  const { jobId } = params;
  if (!jobId) {
    return NextResponse.json({ error: "Missing job id." }, { status: 400 });
  }

  try {
    const provider = getAvatarProvider();
    const result = await provider.getJobStatus(jobId);
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof ProviderError) {
      if (error.statusCode >= 500) {
        console.error("Avatar provider error:", error.message);
      }
      return NextResponse.json({ error: error.message }, { status: error.statusCode });
    }
    console.error("Unexpected error fetching job status:", error);
    return NextResponse.json({ error: "Something went wrong while checking video status." }, { status: 500 });
  }
}
