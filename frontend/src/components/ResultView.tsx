import type { AnalyzeResponse } from "@/lib/api";

import {
  Banknote,
  Building2,
  CalendarDays,
  FileText,
  ListTree,
  Quote,
  ScanText,
  Smile,
  UserRound,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export function ResultView({ result }: { result: AnalyzeResponse }) {
  if (result.status === "error") {
    return (
      <Alert variant="destructive">
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{result.message}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ScanText className="size-4 text-primary" />
            Result
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="text-sm text-muted-foreground">File</div>
          <div className="flex items-center gap-2 font-medium">
            <FileText className="size-4 text-muted-foreground" />
            {result.fileName}
          </div>

          <Separator />

          <div>
            <div className="flex items-center gap-2 text-sm font-medium">
              <Quote className="size-4 text-muted-foreground" />
              Summary
            </div>
            <p className="mt-2 whitespace-pre-wrap text-sm text-foreground/90">
              {result.summary}
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <Smile className="size-4 text-primary" />
              Sentiment
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant="secondary">{result.sentiment}</Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <Banknote className="size-4 text-primary" />
              Amounts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {result.entities.amounts.length ? (
                result.entities.amounts.map((a) => (
                  <Badge key={a} variant="outline">
                    {a}
                  </Badge>
                ))
              ) : (
                <span className="text-sm text-muted-foreground">None</span>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ListTree className="size-4 text-primary" />
            Entities
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-px overflow-hidden rounded-lg border bg-border md:grid-cols-3">
            <EntityTableCell
              title="Names"
              icon={<UserRound className="size-4" />}
              items={result.entities.names}
            />
            <EntityTableCell
              title="Dates"
              icon={<CalendarDays className="size-4" />}
              items={result.entities.dates}
            />
            <EntityTableCell
              title="Organizations"
              icon={<Building2 className="size-4" />}
              items={result.entities.organizations}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function EntityTableCell({
  title,
  icon,
  items,
}: {
  title: string;
  icon: React.ReactNode;
  items: string[];
}) {
  return (
    <div className="bg-card p-3">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        <span className="text-muted-foreground">{icon}</span>
        {title}
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        {items.length ? (
          items.map((x) => (
            <Badge key={x} variant="outline" className="px-2 py-0">
              {x}
            </Badge>
          ))
        ) : (
          <span className="text-sm text-muted-foreground">None</span>
        )}
      </div>
    </div>
  );
}
