export type FileType = "pdf" | "docx" | "image";

export type AnalyzeRequest = {
  fileName: string;
  fileType: FileType;
  fileBase64: string;
};

export type AnalyzeResponse =
  | {
      status: "success";
      fileName: string;
      summary: string;
      entities: {
        names: string[];
        dates: string[];
        organizations: string[];
        amounts: string[];
      };
      sentiment: "Positive" | "Neutral" | "Negative" | string;
    }
  | {
      status: "error";
      fileName?: string;
      message: string;
    };

function getBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
}

export async function analyzeDocument(params: {
  apiKey: string;
  payload: AnalyzeRequest;
}): Promise<AnalyzeResponse> {
  const res = await fetch(`${getBaseUrl()}/api/document-analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": params.apiKey,
    },
    body: JSON.stringify(params.payload),
  });

  const data = (await res.json()) as AnalyzeResponse | { detail?: string };
  if (!res.ok) {
    const msg =
      (data as any)?.message || (data as any)?.detail || `HTTP ${res.status}`;
    return { status: "error", message: msg };
  }

  return data as AnalyzeResponse;
}
