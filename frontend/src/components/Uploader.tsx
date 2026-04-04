"use client";

import type { AnalyzeResponse, FileType } from "@/lib/api";
import { analyzeDocument } from "@/lib/api";
import { fileToBase64, inferFileType } from "@/lib/file";
import { FileText, FileUp, Info, KeyRound, Upload } from "lucide-react";
import { useMemo, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";

export function Uploader({
  defaultApiKey,
  onResult,
}: {
  defaultApiKey?: string;
  onResult: (r: AnalyzeResponse) => void;
}) {
  // Require users to provide their own API key (do not auto-fill from env).
  const [apiKey, setApiKey] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const fileType = useMemo<FileType | null>(() => {
    if (!file) return null;
    return inferFileType(file);
  }, [file]);

  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLocalError(null);

    if (!apiKey.trim()) {
      setLocalError("API key is required");
      return;
    }
    if (!file) {
      setLocalError("Please select a file");
      return;
    }
    if (!fileType) {
      setLocalError("Unsupported file. Upload PDF, DOCX, PNG, JPG, or JPEG.");
      return;
    }

    setLoading(true);
    try {
      const b64 = await fileToBase64(file);
      const payload = {
        fileName: file.name,
        fileType,
        fileBase64: b64,
      };
      const result = await analyzeDocument({ apiKey, payload });
      onResult(result);
    } catch (err: any) {
      setLocalError(err?.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileUp className="size-4 text-primary" />
          Upload
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          {localError ? (
            <Alert variant="destructive">
              <AlertTitle>Request error</AlertTitle>
              <AlertDescription>{localError}</AlertDescription>
            </Alert>
          ) : null}

          <div className="grid gap-6 md:grid-cols-2 md:items-start">
            {/* API key */}
            <div className="space-y-2">
              <Label htmlFor="apiKey" className="flex items-center gap-2">
                <KeyRound className="size-4 text-muted-foreground" />
                API Key
              </Label>
              <Input
                id="apiKey"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk_..."
                autoComplete="off"
              />
              <p className="text-xs text-muted-foreground leading-5">
                Sent as{" "}
                <code className="rounded bg-muted px-1">x-api-key</code>
              </p>
            </div>

            {/* Document */}
            <div className="space-y-2">
              <Label htmlFor="file" className="flex items-center gap-2">
                <FileText className="size-4 text-muted-foreground" />
                Document
              </Label>

              {/* Hidden native picker */}
              <input
                id="file"
                type="file"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                accept=".pdf,.docx,.png,.jpg,.jpeg"
              />

              <div className="grid gap-2">
                <Button
                  type="button"
                  variant="outline"
                  asChild
                  className="w-full justify-center gap-2"
                >
                  <label htmlFor="file" className="cursor-pointer">
                    <Upload className="size-4" />
                    Choose file
                  </label>
                </Button>

                <div className="text-xs text-muted-foreground leading-5">
                  <div className="flex gap-2">
                    <span className="min-w-[70px]">Selected:</span>
                    <span className="font-medium truncate">{file?.name ?? "—"}</span>
                  </div>
                  <div className="flex gap-2">
                    <span className="min-w-[70px]">Type:</span>
                    <span className="font-medium">{fileType ?? "—"}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={loading} className="gap-2">
              {loading ? (
                <>
                  <Spinner className="size-4" />
                  Analyzing…
                </>
              ) : (
                <>
                  <ScanTextIcon className="size-4" />
                  Analyze document
                </>
              )}
            </Button>
            <p className="flex items-center gap-2 text-xs text-muted-foreground">
              <Info className="size-4" />
              Tip: the backend can take a few seconds on first run.
            </p>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function ScanTextIcon(props: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={props.className}
    >
      <path
        d="M4 7V6a2 2 0 0 1 2-2h1M20 7V6a2 2 0 0 0-2-2h-1M4 17v1a2 2 0 0 0 2 2h1M20 17v1a2 2 0 0 1-2 2h-1"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M7 12h10"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}
