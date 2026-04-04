import AnalyzeClient from "@/app/analyze/page_client";
import { ArrowLeft, LinkIcon, ScanText } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

import { Button } from "@/components/ui/button";

export default function AnalyzePage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-background to-muted/30">
      <div className="mx-auto max-w-5xl px-4 py-10">
        <div className="mb-8 flex items-start justify-between gap-4">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
              <ScanText className="size-5 text-primary" />
              Analyze
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Upload a PDF, DOCX or image to extract text, summary, entities and
              sentiment.
            </p>
          </div>

          <Button asChild variant="outline" className="gap-2">
            <Link href="/">
              <ArrowLeft className="size-4" />
              Back
            </Link>
          </Button>
        </div>

        <Suspense>
          <AnalyzeClient />
        </Suspense>
      </div>
    </main>
  );
}
