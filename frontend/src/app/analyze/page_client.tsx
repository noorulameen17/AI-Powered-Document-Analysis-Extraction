"use client";

import { ResultView } from "@/components/ResultView";
import { Uploader } from "@/components/Uploader";
import type { AnalyzeResponse } from "@/lib/api";
import { useState } from "react";

export default function AnalyzeClient() {
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  return (
    <div className="space-y-6">
      <Uploader onResult={setResult} />

      {result ? (
        <ResultView result={result} />
      ) : (
        <div className="rounded-lg border border-dashed bg-gray-50 p-6 text-sm text-gray-500">
          Results will appear here after analysis.
        </div>
      )}
    </div>
  );
}
