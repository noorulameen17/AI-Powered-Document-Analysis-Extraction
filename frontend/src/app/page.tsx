import {
    ArrowRight,
    Braces,
    Cpu,
    FileText,
    ListChecks,
    ScanText,
    Shield,
    Smile,
    Sparkles,
    Tags,
} from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-background to-muted/30">
      <div className="mx-auto max-w-6xl px-4 py-14">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="grid size-9 place-items-center rounded-xl bg-primary text-primary-foreground">
              <Sparkles className="size-4" />
            </div>
            <div className="text-sm font-semibold tracking-tight">
              AI Document Analysis
            </div>
            <Badge variant="outline" className="hidden sm:inline-flex">
              Local • FastAPI • Celery
            </Badge>
          </div>

          <div className="flex items-center gap-2">
            <Button asChild className="gap-2">
              <Link href="/analyze">
                Get started <ArrowRight className="size-4" />
              </Link>
            </Button>
          </div>
        </header>

        <section className="mt-14 grid gap-8 lg:grid-cols-2 lg:items-stretch">
          <Card className="h-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-3xl sm:text-4xl">
                <Sparkles className="size-6 text-primary" />
                Turn documents into structured insights.
              </CardTitle>
              <CardDescription className="text-base">
                Upload a PDF, DOCX, or image. Extract text (OCR for scans),
                generate a summary, detect entities, and classify sentiment —
                returned in a single JSON response.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary" className="gap-1.5">
                  <FileText className="size-3.5" /> PDF / DOCX
                </Badge>
                <Badge variant="secondary" className="gap-1.5">
                  <ScanText className="size-3.5" /> OCR Images
                </Badge>
                <Badge variant="secondary" className="gap-1.5">
                  <Tags className="size-3.5" /> Entities
                </Badge>
                <Badge variant="secondary" className="gap-1.5">
                  <Smile className="size-3.5" /> Sentiment
                </Badge>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                <Button asChild size="lg" className="gap-2">
                  <Link href="/analyze">
                    Analyze a document <ArrowRight className="size-4" />
                  </Link>
                </Button>
                <Button asChild size="lg" variant="outline" className="gap-2">
                  <a href="#features">
                    View features <ArrowRight className="size-4" />
                  </a>
                </Button>
              </div>

              <div className="text-xs text-muted-foreground">
                Runs locally with your dockerized backend. No paid AI APIs
                required.
              </div>
            </CardContent>
          </Card>

          <Card className="h-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Braces className="size-4 text-muted-foreground" />
                API response (example)
              </CardTitle>
              <CardDescription>
                What you get back from <code>/api/document-analyze</code>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="overflow-auto rounded-xl bg-black p-4 text-xs text-white">
{`{
  "status": "success",
  "fileName": "invoice.pdf",
  "summary": "...",
  "entities": {
    "names": ["John Doe"],
    "dates": ["2026-04-03"],
    "organizations": ["Acme Corp"],
    "amounts": ["$1,245.00"]
  },
  "sentiment": "Neutral"
}`}
              </pre>

              <Separator className="my-5" />

              <div className="grid gap-3 sm:grid-cols-3">
                <MiniStat icon={Cpu} title="Local" body="No external LLM" />
                <MiniStat icon={Shield} title="Secured" body="x-api-key" />
                <MiniStat icon={Sparkles} title="Clean" body="JSON output" />
              </div>
            </CardContent>
          </Card>
        </section>

        <section id="features" className="mt-16">
          <div className="flex items-end justify-between gap-4">
            <div>
              <h2 className="flex items-center gap-2 text-2xl font-bold tracking-tight">
                <ListChecks className="size-5 text-primary" />
                Features
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Built for the hackathon spec: base64 input, multi-format support,
                summary, entities, and sentiment.
              </p>
            </div>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Feature
              icon={FileText}
              title="Multi-format input"
              body="PDF, DOCX, and images (PNG/JPG/JPEG)."
            />
            <Feature
              icon={ScanText}
              title="OCR for scans"
              body="Tesseract OCR extracts text from images and scanned documents."
            />
            <Feature
              icon={Tags}
              title="Entity extraction"
              body="Names, dates, organizations, and currency/amount detection."
            />
            <Feature
              icon={Sparkles}
              title="Fast summary"
              body="Stable heuristic summarization to avoid token-limit surprises."
            />
            <Feature
              icon={Smile}
              title="Sentiment"
              body="Local transformer model for sentiment classification."
            />
            <Feature
              icon={Shield}
              title="Simple auth"
              body="API key required via x-api-key header."
            />
          </div>
        </section>

        <footer className="mt-16">
          <Separator />
          <div className="mt-8 flex flex-col gap-2 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
            <div>Built with Next.js + shadcn/ui + FastAPI + Celery + Redis.</div>
            <div>
              <Button asChild variant="link" className="h-auto p-0">
                <Link href="/analyze">Open analyzer</Link>
              </Button>
            </div>
          </div>
        </footer>
      </div>
    </main>
  );
}

function Feature({
  icon: Icon,
  title,
  body,
}: {
  icon: React.ElementType;
  title: string;
  body: string;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <div className="grid size-8 place-items-center rounded-lg bg-muted">
            <Icon className="size-4" />
          </div>
          <CardTitle className="text-base">{title}</CardTitle>
        </div>
        <CardDescription>{body}</CardDescription>
      </CardHeader>
    </Card>
  );
}

function MiniStat({
  icon: Icon,
  title,
  body,
}: {
  icon: React.ElementType;
  title: string;
  body: string;
}) {
  return (
    <div className="flex items-center gap-2 rounded-xl border bg-card p-3">
      <div className="grid size-8 place-items-center rounded-lg bg-muted">
        <Icon className="size-4" />
      </div>
      <div>
        <div className="text-sm font-medium">{title}</div>
        <div className="text-xs text-muted-foreground">{body}</div>
      </div>
    </div>
  );
}
