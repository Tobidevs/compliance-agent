"use client";

import { type CSSProperties, type FormEvent, useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import {
  type ControlValidation,
  type StreamEvent,
  type ValidationFinding,
} from "@/lib/utils";

const frameworks = ["soc2-source-code"];
const categories = ["Category A", "Category B", "Category C"];
const sourceCodeOptions = [
  "Change Management & SDLC",
  "Identity & Access Management",
  "Data Protection & Privacy",
  "Processing Integrity",
  "Network & Systems Security",
  "Logging & Monitoring",
  "Operations & Incident Management",
];

const statusOrder: Record<ControlValidation["status"], number> = {
  FAIL: 0,
  PARTIAL: 1,
  NO_EVIDENCE: 2,
  PASS: 3,
};

const severityOrder = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

function clamp(value: number, min = 0, max = 100) {
  return Math.min(max, Math.max(min, value));
}

function formatPercent(value: number) {
  return `${Math.round(value)}%`;
}

function formatDecimalPercent(value: number) {
  return `${value.toFixed(value % 1 === 0 ? 0 : 1)}%`;
}

function getControlKey(control: ControlValidation) {
  return `${control.regulation_id}::${control.title}`;
}

function getStatusBadgeVariant(status: ControlValidation["status"]) {
  if (status === "FAIL") return "strong";
  if (status === "PARTIAL") return "accent";
  if (status === "NO_EVIDENCE") return "muted";
  return "neutral";
}

function getSeverityTone(
  severity: ControlValidation["severity"] | undefined,
) {
  if (severity === "critical") {
    return {
      solid: "#9a3412",
      text: "#9a3412",
      border: "rgb(154 52 18 / 0.30)",
      background: "rgb(154 52 18 / 0.10)",
    };
  }
  if (severity === "high") {
    return {
      solid: "#c2410c",
      text: "#c2410c",
      border: "rgb(194 65 12 / 0.28)",
      background: "rgb(194 65 12 / 0.10)",
    };
  }
  if (severity === "medium") {
    return {
      solid: "#ea580c",
      text: "#ea580c",
      border: "rgb(234 88 12 / 0.24)",
      background: "rgb(234 88 12 / 0.08)",
    };
  }
  return {
    solid: "#fdba74",
    text: "#c2410c",
    border: "rgb(253 186 116 / 0.60)",
    background: "rgb(253 186 116 / 0.18)",
  };
}

function getStatusBarTone(status: ControlValidation["status"]) {
  if (status === "FAIL") return "bg-black";
  if (status === "PARTIAL") return "bg-orange-500";
  if (status === "NO_EVIDENCE") return "bg-black/20";
  return "bg-orange-400";
}

function getStatusSliceColor(status: ControlValidation["status"]) {
  if (status === "FAIL") return "rgb(249 115 22 / 0.38)";
  if (status === "PARTIAL") return "rgb(249 115 22 / 0.68)";
  if (status === "NO_EVIDENCE") return "rgb(255 176 57 / 0.20)";
  return "#f97316";
}

function getFindingBadgeVariant(type: "violation" | "pass" | "gap") {
  if (type === "violation") return "strong";
  if (type === "gap") return "accent";
  return "neutral";
}

function formatFrontendErrorMessage(message: string) {
  const normalizedMessage = message.trim();
  const loweredMessage = normalizedMessage.toLowerCase();

  if (
    loweredMessage.includes("rate limit") ||
    loweredMessage.includes("too many requests") ||
    loweredMessage.includes("429") ||
    loweredMessage.includes("quota")
  ) {
    return "Rate limit reached. Please wait a moment and try again.";
  }

  if (
    loweredMessage.includes("failed to fetch") ||
    loweredMessage.includes("networkerror") ||
    loweredMessage.includes("network request failed")
  ) {
    return "Unable to reach the compliance API. Please check that the backend is running and try again.";
  }

  if (
    loweredMessage.includes("not found") &&
    loweredMessage.includes("repo")
  ) {
    return "Repository not found or inaccessible. Please verify the owner and repository name.";
  }

  return normalizedMessage || "Something went wrong while running the compliance check.";
}

function SeverityBadge({
  severity,
}: {
  severity: NonNullable<ControlValidation["severity"]>;
}) {
  const tone = getSeverityTone(severity);

  return (
    <Badge
      variant="neutral"
      className="capitalize"
      style={{
        color: tone.text,
        borderColor: tone.border,
        backgroundColor: tone.background,
      }}
    >
      {severity}
    </Badge>
  );
}

function parseControlValidation(item: unknown): ControlValidation | null {
  if (!item || typeof item !== "object") return null;

  const candidate = item as Record<string, unknown>;
  if (
    typeof candidate.regulation_id !== "string" ||
    typeof candidate.title !== "string" ||
    typeof candidate.status !== "string" ||
    typeof candidate.confidence !== "number" ||
    !Array.isArray(candidate.findings) ||
    typeof candidate.overall_reasoning !== "string"
  ) {
    return null;
  }

  const parsedFindings: ValidationFinding[] = [];

  for (const finding of candidate.findings) {
    if (!finding || typeof finding !== "object") continue;
    const parsedFinding = finding as Record<string, unknown>;
    if (
      typeof parsedFinding.type !== "string" ||
      typeof parsedFinding.description !== "string" ||
      typeof parsedFinding.reasoning !== "string"
    ) {
      continue;
    }

    const evidenceRef =
      parsedFinding.evidence_ref &&
      typeof parsedFinding.evidence_ref === "object" &&
      typeof (parsedFinding.evidence_ref as { snippet?: unknown }).snippet ===
        "string"
        ? {
            snippet: (parsedFinding.evidence_ref as { snippet: string })
              .snippet,
          }
        : null;

    parsedFindings.push({
      type: parsedFinding.type as "violation" | "pass" | "gap",
      description: parsedFinding.description,
      evidence_ref: evidenceRef,
      reasoning: parsedFinding.reasoning,
    });
  }

  return {
    regulation_id: candidate.regulation_id,
    title: candidate.title,
    status: candidate.status as ControlValidation["status"],
    severity:
      typeof candidate.severity === "string"
        ? (candidate.severity as ControlValidation["severity"])
        : null,
    confidence: candidate.confidence,
    confidence_label:
      typeof candidate.confidence_label === "string"
        ? (candidate.confidence_label as ControlValidation["confidence_label"])
        : "Inconclusive",
    findings: parsedFindings,
    overall_reasoning: candidate.overall_reasoning,
  };
}

function collectValidationCandidates(payload: unknown): unknown[] {
  if (!payload) return [];

  if (Array.isArray(payload)) {
    return payload.flatMap((item) =>
      Array.isArray(item) ? collectValidationCandidates(item) : [item],
    );
  }

  if (typeof payload !== "object") {
    return [];
  }

  const payloadRecord = payload as Record<string, unknown>;

  if (Array.isArray(payloadRecord.validation_results)) {
    return collectValidationCandidates(payloadRecord.validation_results);
  }

  if (
    payloadRecord.data &&
    typeof payloadRecord.data === "object" &&
    !Array.isArray(payloadRecord.data)
  ) {
    const nestedDataResults = collectValidationCandidates(payloadRecord.data);
    if (nestedDataResults.length) {
      return nestedDataResults;
    }
  }

  return Object.values(payloadRecord).flatMap((value) =>
    collectValidationCandidates(value),
  );
}

function normalizeValidationPayload(payload: unknown): ControlValidation[] {
  return collectValidationCandidates(payload)
    .map(parseControlValidation)
    .filter((item): item is ControlValidation => Boolean(item));
}

function sortValidationResults(results: ControlValidation[]) {
  return [...results].sort((left, right) => {
    const statusDifference =
      statusOrder[left.status] - statusOrder[right.status];
    if (statusDifference !== 0) return statusDifference;

    const leftSeverity =
      left.severity && left.severity in severityOrder
        ? severityOrder[left.severity]
        : Number.MAX_SAFE_INTEGER;
    const rightSeverity =
      right.severity && right.severity in severityOrder
        ? severityOrder[right.severity]
        : Number.MAX_SAFE_INTEGER;
    if (leftSeverity !== rightSeverity) return leftSeverity - rightSeverity;

    return right.confidence - left.confidence;
  });
}

function MetricRail({
  label,
  value,
  caption,
}: {
  label: string;
  value: string;
  caption: string;
}) {
  return (
    <div className="space-y-2 py-5">
      <p className="text-[11px] uppercase tracking-[0.22em] text-black/45">
        {label}
      </p>
      <p className="text-3xl font-semibold tracking-tight text-black">
        {value}
      </p>
      <p className="max-w-sm text-sm leading-6 text-black/55">{caption}</p>
    </div>
  );
}

function ConfidenceRing({ value }: { value: number }) {
  const radius = 48;
  const circumference = 2 * Math.PI * radius;
  const normalizedValue = clamp(value);
  const dashOffset = circumference - (normalizedValue / 100) * circumference;

  const ringStyle = {
    "--ring-length": `${circumference}`,
    "--ring-offset": `${dashOffset}`,
  } as CSSProperties;

  return (
    <div className="flex items-center gap-5">
      <div className="relative flex h-32 w-32 items-center justify-center">
        <svg
          viewBox="0 0 120 120"
          className="h-full w-full -rotate-90"
          aria-hidden="true"
        >
          <circle
            cx="60"
            cy="60"
            r={radius}
            className="fill-none stroke-black/8"
            strokeWidth="8"
          />
          <circle
            cx="60"
            cy="60"
            r={radius}
            className="ring-progress fill-none stroke-orange-500"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            style={ringStyle}
          />
        </svg>
        <div className="absolute flex flex-col items-center">
          <span className="text-3xl font-semibold tracking-tight text-black">
            {Math.round(normalizedValue)}
          </span>
          <span className="text-[11px] uppercase tracking-[0.24em] text-black/45">
            Confidence
          </span>
        </div>
      </div>
      <div className="max-w-[14rem] space-y-2 text-sm leading-6 text-black/55">
        <p>Average confidence across all validated controls.</p>
        <p>
          Lower values indicate broader uncertainty or limited evidence depth in
          the repository scan.
        </p>
      </div>
    </div>
  );
}

function OutcomeDonutChart({
  segments,
  total,
}: {
  segments: Array<{
    label: ControlValidation["status"];
    count: number;
    value: number;
    color: string;
  }>;
  total: number;
}) {
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const arcSegments = segments.map((segment) => {
    const previousLength = segments
      .slice(0, segments.indexOf(segment))
      .reduce(
        (sum, currentSegment) =>
          sum + (currentSegment.value / 100) * circumference,
        0,
      );

    return {
      ...segment,
      segmentLength: (segment.value / 100) * circumference,
      strokeDashoffset: -previousLength,
    };
  });

  return (
    <div className="grid gap-8 lg:grid-cols-[240px_1fr] lg:items-center">
      <div className="flex justify-center lg:justify-start">
        <div className="relative flex h-56 w-56 items-center justify-center">
          <svg viewBox="0 0 140 140" className="h-full w-full" aria-hidden="true">
            <circle
              cx="70"
              cy="70"
              r={radius}
              className="fill-none stroke-black/8"
              strokeWidth="18"
            />
            <g transform="rotate(-90 70 70)">
              {arcSegments.map((segment) =>
                segment.count ? (
                  <circle
                    key={segment.label}
                    cx="70"
                    cy="70"
                    r={radius}
                    fill="none"
                    stroke={segment.color}
                    strokeWidth="18"
                    strokeDasharray={`${segment.segmentLength} ${circumference}`}
                    strokeDashoffset={segment.strokeDashoffset}
                  />
                ) : null,
              )}
            </g>
          </svg>

          <div className="absolute flex flex-col items-center text-center">
            <span className="text-4xl font-semibold tracking-tight text-black">
              {total}
            </span>
            <span className="text-[11px] uppercase tracking-[0.24em] text-black/45">
              Controls
            </span>
            <span className="mt-2 text-sm text-black/55">100% distribution</span>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {segments.map((segment) => (
          <div
            key={segment.label}
            className="grid gap-2 border-b border-black/8 pb-3 sm:grid-cols-[1fr_88px_72px] sm:items-center"
          >
            <div className="flex items-center gap-3">
              <span
                className="h-3 w-3 rounded-full"
                style={{ backgroundColor: segment.color }}
              />
              <span className="text-sm font-medium tracking-[0.02em] text-black">
                {segment.label.replace("_", " ")}
              </span>
              <span className="text-sm text-black/50">
                {segment.count} {segment.count === 1 ? "control" : "controls"}
              </span>
            </div>
            <span className="text-sm text-black/55 sm:text-right">
              {formatDecimalPercent(segment.value)}
            </span>
            <span className="text-sm font-medium text-black sm:text-right">
              {segment.count}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  const apiBaseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
  const [framework, setFramework] = useState("");
  const [category, setCategory] = useState("");
  const [sourceCodeCategories, setSourceCodeCategories] = useState<string[]>(
    [],
  );
  const [repoName, setRepoName] = useState("");
  const [repoOwner, setRepoOwner] = useState("");

  const [status, setStatus] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [statusTick, setStatusTick] = useState(0);

  const [validationResults, setValidationResults] = useState<
    ControlValidation[]
  >([]);
  const [rawValidationJson, setRawValidationJson] = useState("");
  const [selectedControlId, setSelectedControlId] = useState("");
  const [showRawOutput, setShowRawOutput] = useState(false);
  const [showForm, setShowForm] = useState(true);
  const [showStatus, setShowStatus] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const sortedResults = sortValidationResults(validationResults);

  const resolvedSelectedControlId = sortedResults.some(
    (control) => getControlKey(control) === selectedControlId,
  )
    ? selectedControlId
    : sortedResults[0]
      ? getControlKey(sortedResults[0])
      : "";

  const selectedControl =
    sortedResults.find(
      (control) => getControlKey(control) === resolvedSelectedControlId,
    ) ?? null;

  const totalControls = sortedResults.length;
  const statusCounts = sortedResults.reduce(
    (accumulator, control) => {
      accumulator[control.status] += 1;
      return accumulator;
    },
    {
      PASS: 0,
      PARTIAL: 0,
      FAIL: 0,
      NO_EVIDENCE: 0,
    },
  );

  const severityCounts = sortedResults.reduce(
    (accumulator, control) => {
      if (control.severity) {
        accumulator[control.severity] += 1;
      }
      return accumulator;
    },
    {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
    },
  );

  const findingCounts = sortedResults.reduce(
    (accumulator, control) => {
      for (const finding of control.findings) {
        accumulator[finding.type] += 1;
      }
      return accumulator;
    },
    {
      violation: 0,
      gap: 0,
      pass: 0,
    },
  );

  const postureScore = totalControls
    ? ((statusCounts.PASS + statusCounts.PARTIAL * 0.5) / totalControls) * 100
    : 0;
  const evidenceCoverage = totalControls
    ? ((totalControls - statusCounts.NO_EVIDENCE) / totalControls) * 100
    : 0;
  const averageConfidence = totalControls
    ? (sortedResults.reduce((sum, control) => sum + control.confidence, 0) /
        totalControls) *
      100
    : 0;
  const severityTotal =
    severityCounts.critical +
    severityCounts.high +
    severityCounts.medium +
    severityCounts.low;
  const findingTotal =
    findingCounts.violation + findingCounts.gap + findingCounts.pass;

  const statusRows: Array<{
    label: ControlValidation["status"];
    count: number;
    value: number;
    color: string;
  }> = [
    {
      label: "FAIL",
      count: statusCounts.FAIL,
      value: totalControls ? (statusCounts.FAIL / totalControls) * 100 : 0,
      color: getStatusSliceColor("FAIL"),
    },
    {
      label: "PARTIAL",
      count: statusCounts.PARTIAL,
      value: totalControls ? (statusCounts.PARTIAL / totalControls) * 100 : 0,
      color: getStatusSliceColor("PARTIAL"),
    },
    {
      label: "NO_EVIDENCE",
      count: statusCounts.NO_EVIDENCE,
      value: totalControls
        ? (statusCounts.NO_EVIDENCE / totalControls) * 100
        : 0,
      color: getStatusSliceColor("NO_EVIDENCE"),
    },
    {
      label: "PASS",
      count: statusCounts.PASS,
      value: totalControls ? (statusCounts.PASS / totalControls) * 100 : 0,
      color: getStatusSliceColor("PASS"),
    },
  ];

  const toggleSourceCodeCategory = (value: string) => {
    setSourceCodeCategories((prev) =>
      prev.includes(value)
        ? prev.filter((item) => item !== value)
        : [...prev, value],
    );
  };

  useEffect(() => {
    if (!errorMessage) return;

    const timeoutId = window.setTimeout(() => {
      setErrorMessage("");
    }, 7000);

    return () => window.clearTimeout(timeoutId);
  }, [errorMessage]);

  const resetToFormWithError = (message: string) => {
    const formattedMessage = formatFrontendErrorMessage(message);

    setErrorMessage(formattedMessage);
    setStatus(formattedMessage);
    setStatusTick((prev) => prev + 1);
    setLoading(false);
    setShowStatus(false);
    setShowResults(false);
    setShowForm(true);
  };

  async function runComplianceAgent() {
    try {
      setLoading(true);
      setStatus("Running compliance agent...");
      setErrorMessage("");

      const response = await fetch(`${apiBaseUrl}/api/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          framework,
          category,
          source_code_categories: sourceCodeCategories,
          repo_owner: repoOwner,
          repo_name: repoName,
        }),
      });

      if (!response.ok) {
        let errorDetail = `Request failed with status ${response.status}`;

        try {
          const errorPayload = (await response.json()) as {
            detail?: string;
            message?: string;
          };
          errorDetail =
            errorPayload.detail ??
            errorPayload.message ??
            errorDetail;
        } catch {
          if (response.statusText) {
            errorDetail = response.statusText;
          }
        }

        throw new Error(errorDetail);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("The API returned an empty response stream.");
      }

      const decoder = new TextDecoder("utf-8");
      let result = "";
      let runCompleted = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        result += decoder.decode(value, { stream: true });
        const events = result.split("\n\n");

        result = events.pop() || "";

        for (const event of events) {
          const trimmed = event.trim();
          if (!trimmed || !trimmed.startsWith("data: ")) continue;

          const jsonString = trimmed.replace("data: ", "");
          const data: StreamEvent = JSON.parse(jsonString);

          if (data.type === "status") {
            const statusMessage =
              data.message ??
              (typeof data.data === "string" ? data.data : data.data?.message);
            if (statusMessage) {
              setStatus(statusMessage);
            }
            setStatusTick((prev) => prev + 1);
          } else if (data.type === "token") {
            setResponse((prev) => prev + data.token);
          } else if (data.type === "error") {
            resetToFormWithError(data.message);
            return;
          } else if (data.type === "update" || data.type === "updates") {
            const normalized = normalizeValidationPayload(data.data);
            setValidationResults(normalized);
            setRawValidationJson(JSON.stringify(normalized, null, 2));
          } else if (data.type === "done") {
            runCompleted = true;
            setStatus("Compliance agent run complete.");
            setStatusTick((prev) => prev + 1);
            setLoading(false);
            setShowStatus(false);
            setTimeout(() => setShowResults(true), 250);
            return;
          }
        }
      }

      if (!runCompleted) {
        throw new Error(
          "The compliance run ended before a completion event was received.",
        );
      }
    } catch (error: unknown) {
      const message =
        error instanceof Error
          ? error.message
          : "Unknown compliance agent error.";
      resetToFormWithError(message);
    }
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setShowForm(false);
    setShowStatus(true);
    setShowResults(false);
    setResponse("");
    setValidationResults([]);
    setRawValidationJson("");
    setSelectedControlId("");
    setShowRawOutput(false);
    setErrorMessage("");
    runComplianceAgent();
  };

  const screenBase =
    "absolute inset-0 overflow-y-auto px-6 py-16 transition-opacity duration-500 md:px-8 xl:px-12";
  const screenVisible = "opacity-100 pointer-events-auto";
  const screenHidden = "opacity-0 pointer-events-none";

  return (
    <main className="relative min-h-screen bg-white">
      {errorMessage ? (
        <div className="pointer-events-none fixed inset-x-0 top-5 z-50 flex justify-center px-4">
          <div
            className="pointer-events-auto flex w-full max-w-xl items-start justify-between gap-4 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-left shadow-lg shadow-red-100/70"
            role="alert"
            aria-live="assertive"
          >
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-red-600">
                Compliance run failed
              </p>
              <p className="mt-2 text-sm leading-6 text-red-950">
                {errorMessage}
              </p>
            </div>
            <button
              type="button"
              className="shrink-0 rounded-full border border-red-200 px-3 py-1 text-xs font-medium text-red-700 transition hover:bg-red-100"
              onClick={() => setErrorMessage("")}
            >
              Dismiss
            </button>
          </div>
        </div>
      ) : null}

      <section
        className={`${screenBase} ${showForm ? screenVisible : screenHidden}`}
        aria-hidden={!showForm}
      >
        <div className="animate-fade-up mx-auto flex w-full max-w-2xl flex-col items-center text-center">
          <p className="text-sm uppercase tracking-[0.2em] text-orange-500">
            Compliance Validation
          </p>
          <h1 className="mt-3 text-3xl font-semibold text-black sm:text-4xl">
            SOC 2 Readiness Intake
          </h1>
          <p className="mt-3 max-w-xl text-sm text-black/60 sm:text-base">
            Provide repository details and pick the validation scope. We will
            use these inputs to shape the compliance review.
          </p>
        </div>

        <form
          className="animate-fade-up-delay mx-auto mt-12 w-full max-w-2xl space-y-6"
          onSubmit={handleSubmit}
        >
          <div className="grid gap-2">
            <Label htmlFor="framework">Framework</Label>
            <Select value={framework} onValueChange={setFramework}>
              <SelectTrigger id="framework">
                <SelectValue placeholder="Select framework" />
              </SelectTrigger>
              <SelectContent>
                {frameworks.map((value) => (
                  <SelectItem key={value} value={value}>
                    {value}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="category">Category</Label>
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger id="category">
                <SelectValue placeholder="Select category" />
              </SelectTrigger>
              <SelectContent>
                {categories.map((value) => (
                  <SelectItem key={value} value={value}>
                    {value}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-3">
            <div className="flex items-center justify-between">
              <Label>Source code categories</Label>
              <span className="text-xs text-black/45">
                {sourceCodeCategories.length} selected
              </span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {sourceCodeOptions.map((value) => (
                <label
                  key={value}
                  className="flex items-start gap-3 rounded-md border border-black/10 px-3 py-2 text-left text-sm text-black"
                >
                  <Checkbox
                    checked={sourceCodeCategories.includes(value)}
                    onCheckedChange={() => toggleSourceCodeCategory(value)}
                  />
                  <span className="leading-snug">{value}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="repo-name">Repository name</Label>
            <Input
              id="repo-name"
              placeholder="compliance-agent"
              value={repoName}
              onChange={(event) => setRepoName(event.target.value)}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="repo-owner">Repository owner</Label>
            <Input
              id="repo-owner"
              placeholder="org-or-user"
              value={repoOwner}
              onChange={(event) => setRepoOwner(event.target.value)}
            />
          </div>

          <div className="flex items-center justify-end">
            <Button type="submit" disabled={loading}>
              {loading ? "Running..." : "Run Compliance"}
            </Button>
          </div>
        </form>
      </section>

      <section
        className={`${screenBase} ${showStatus ? screenVisible : screenHidden}`}
        aria-hidden={!showStatus}
      >
        <div className="mx-auto flex w-full max-w-2xl flex-col items-center text-center">
          <p className="text-xs uppercase tracking-[0.3em] text-orange-500">
            Compliance Validation
          </p>
          <h2 className="mt-4 text-2xl font-semibold text-black sm:text-3xl">
            Running Compliance Checks
          </h2>
          <p className="mt-3 max-w-lg text-sm text-black/60">
            We are analyzing evidence and validating controls. Status updates
            appear as each workflow step completes.
          </p>

          <div className="mt-8 w-full rounded-2xl border border-black/10 bg-white/80 px-6 py-6 shadow-sm">
            <div
              key={statusTick}
              className="animate-status text-base text-black"
            >
              {status || "Initializing compliance workflow..."}
            </div>
            <div className="status-bar-track mt-4">
              <div className="status-bar-fill" />
            </div>
          </div>

          {response ? (
            <div className="mt-8 w-full rounded-2xl border border-black/10 bg-white/70 px-6 py-5 text-left">
              <p className="text-xs uppercase tracking-[0.2em] text-black/50">
                Streamed output
              </p>
              <p className="mt-3 max-h-48 overflow-y-auto text-sm text-black/70">
                {response}
              </p>
            </div>
          ) : null}
        </div>
      </section>

      <section
        className={`${screenBase} ${showResults ? screenVisible : screenHidden}`}
        aria-hidden={!showResults}
      >
        <div className="animate-screen-enter w-full">
          <div className="grid gap-6 xl:grid-cols-[1.4fr_0.6fr] xl:items-end">
            <div className="space-y-4">
              <p className="text-xs uppercase tracking-[0.3em] text-orange-500">
                Compliance Validation
              </p>
              <div className="space-y-3">
                <h2 className="text-3xl font-semibold tracking-tight text-black sm:text-4xl">
                  Validation Results
                </h2>
                <p className="max-w-3xl text-sm leading-7 text-black/60 sm:text-base">
                  A structured view of control outcomes, evidence confidence,
                  and the findings produced by the compliance workflow.
                </p>
              </div>
            </div>

            <div className="grid gap-3 text-sm text-black/60 sm:grid-cols-2 xl:text-right">
              <div>
                <p className="text-[11px] uppercase tracking-[0.2em] text-black/40">
                  Framework
                </p>
                <p className="mt-1 text-base font-medium text-black">
                  {framework || "SOC 2"}
                </p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-[0.2em] text-black/40">
                  Repository
                </p>
                <p className="mt-1 text-base font-medium text-black">
                  {repoOwner && repoName
                    ? `${repoOwner}/${repoName}`
                    : "Repository not provided"}
                </p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-[0.2em] text-black/40">
                  Category
                </p>
                <p className="mt-1 text-base font-medium text-black">
                  {category || "Not specified"}
                </p>
              </div>
              <div>
                <p className="text-[11px] uppercase tracking-[0.2em] text-black/40">
                  Scope
                </p>
                <p className="mt-1 text-base font-medium text-black">
                  {sourceCodeCategories.length
                    ? `${sourceCodeCategories.length} source code scopes`
                    : "No scope selected"}
                </p>
              </div>
            </div>
          </div>

          <Separator className="mt-10" />

          <div className="grid gap-6 py-4 md:grid-cols-2 xl:grid-cols-4 xl:gap-10">
            <MetricRail
              label="Posture"
              value={formatPercent(postureScore)}
              caption="Weighted readiness score using pass and partial outcomes."
            />
            <MetricRail
              label="Evidence Coverage"
              value={formatPercent(evidenceCoverage)}
              caption="Controls with repository evidence, excluding no-evidence outcomes."
            />
            <MetricRail
              label="Average Confidence"
              value={formatPercent(averageConfidence)}
              caption="Mean confidence score across the validation set."
            />
            <MetricRail
              label="Controls Reviewed"
              value={String(totalControls)}
              caption="Total control validations returned by the compliance agent."
            />
          </div>

          <Separator />

          <div className="grid gap-10 py-10 xl:grid-cols-[1.1fr_0.9fr]">
            <div className="space-y-8">
              <div>
                <div className="mb-5 flex items-center justify-between">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.22em] text-black/45">
                      Outcome distribution
                    </p>
                    <p className="mt-2 text-sm text-black/55">
                      Status mix across all validated controls.
                    </p>
                  </div>
                  <Badge variant="accent">{totalControls} controls</Badge>
                </div>

                <OutcomeDonutChart segments={statusRows} total={totalControls} />
              </div>

              <Separator />

              <div className="grid gap-8 lg:grid-cols-2">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.22em] text-black/45">
                    Severity mix
                  </p>
                  <p className="mt-2 text-sm text-black/55">
                    Only controls carrying severity labels are included.
                  </p>

                  <div className="mt-6 overflow-hidden rounded-full bg-black/8">
                    <div className="flex h-3 w-full">
                      {(["critical", "high", "medium", "low"] as const).map(
                        (level) => {
                          const value = severityCounts[level];
                          const width = severityTotal
                            ? (value / severityTotal) * 100
                            : 0;
                          const tone = getSeverityTone(level);

                          return width ? (
                            <div
                              key={level}
                              className="progress-indicator h-full"
                              style={{
                                width: `${width}%`,
                                backgroundColor: tone.solid,
                              }}
                            />
                          ) : null;
                        },
                      )}
                    </div>
                  </div>

                  <div className="mt-5 grid gap-3 text-sm text-black/60 sm:grid-cols-2">
                    {(["critical", "high", "medium", "low"] as const).map(
                      (level) => (
                        <div
                          key={level}
                          className="flex items-center justify-between border-b border-black/8 pb-2"
                        >
                          <span className="flex items-center gap-2 capitalize">
                            <span
                              className="h-2.5 w-2.5 rounded-full"
                              style={{ backgroundColor: getSeverityTone(level).solid }}
                            />
                            {level}
                          </span>
                          <span className="font-medium text-black">
                            {severityCounts[level]}
                          </span>
                        </div>
                      ),
                    )}
                  </div>
                </div>

                <div>
                  <p className="text-[11px] uppercase tracking-[0.22em] text-black/45">
                    Findings composition
                  </p>
                  <p className="mt-2 text-sm text-black/55">
                    Breakdown of pass signals, gaps, and violations.
                  </p>

                  <div className="mt-6 space-y-4">
                    {(
                      [
                        { key: "violation", label: "Violations" },
                        { key: "gap", label: "Gaps" },
                        { key: "pass", label: "Pass signals" },
                      ] as const
                    ).map((item) => {
                      const count = findingCounts[item.key];
                      const percentage = findingTotal
                        ? (count / findingTotal) * 100
                        : 0;

                      return (
                        <div
                          key={item.key}
                          className="grid gap-2 sm:grid-cols-[120px_1fr_56px] sm:items-center"
                        >
                          <span className="text-sm text-black/60">
                            {item.label}
                          </span>
                          <Progress
                            value={percentage}
                            indicatorClassName={
                              item.key === "violation"
                                ? "bg-black"
                                : item.key === "gap"
                                  ? "bg-orange-500"
                                  : "bg-orange-300"
                            }
                          />
                          <span className="text-right text-sm font-medium text-black">
                            {count}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>

            <div className="xl:border-l xl:border-black/10 xl:pl-10">
              <p className="text-[11px] uppercase tracking-[0.22em] text-black/45">
                Confidence ring
              </p>
              <p className="mt-2 mb-6 text-sm text-black/55">
                A quick signal for how decisive the agent was across the full
                result set.
              </p>
              <ConfidenceRing value={averageConfidence} />
            </div>
          </div>

          <Separator />

          <div className="grid gap-10 py-10 xl:grid-cols-[0.95fr_1.05fr]">
            <div>
              <div className="mb-6 flex items-end justify-between gap-4">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.22em] text-black/45">
                    Control explorer
                  </p>
                  <p className="mt-2 text-sm text-black/55">
                    Controls are ordered by risk first, then confidence.
                  </p>
                </div>
                <Badge variant="muted">
                  {totalControls ? `${totalControls} loaded` : "No controls"}
                </Badge>
              </div>

              <div className="border-t border-black/10">
                <div className="hidden grid-cols-[110px_1.4fr_120px_120px_160px_80px] gap-4 border-b border-black/10 py-3 text-[11px] uppercase tracking-[0.2em] text-black/40 lg:grid">
                  <span>Control</span>
                  <span>Title</span>
                  <span>Status</span>
                  <span>Severity</span>
                  <span>Confidence</span>
                  <span className="text-right">Findings</span>
                </div>

                {sortedResults.length ? (
                  sortedResults.map((control) => {
                    const isSelected =
                      getControlKey(control) ===
                      getControlKey(selectedControl ?? control);

                    return (
                      <button
                        key={getControlKey(control)}
                        type="button"
                        onClick={() =>
                          setSelectedControlId(getControlKey(control))
                        }
                        className={`group w-full border-b border-black/8 py-5 text-left transition-colors duration-200 ${
                          isSelected
                            ? "border-black/20"
                            : "hover:border-orange-400/40"
                        }`}
                      >
                        <div className="grid gap-4 lg:grid-cols-[110px_1.4fr_120px_120px_160px_80px] lg:items-center">
                          <div className="space-y-1">
                            <p className="text-sm font-medium text-black">
                              {control.regulation_id}
                            </p>
                            <p className="text-xs uppercase tracking-[0.18em] text-black/35 lg:hidden">
                              Control
                            </p>
                          </div>

                          <div>
                            <p className="text-sm font-medium leading-6 text-black">
                              {control.title}
                            </p>
                          </div>

                          <div className="flex items-center gap-2">
                            <Badge
                              variant={getStatusBadgeVariant(control.status)}
                            >
                              {control.status.replace("_", " ")}
                            </Badge>
                          </div>

                          <div>
                            {control.severity ? (
                              <SeverityBadge severity={control.severity} />
                            ) : (
                              <span className="text-sm text-black/35">
                                None
                              </span>
                            )}
                          </div>

                          <div className="space-y-2">
                            <div className="flex items-center justify-between text-xs uppercase tracking-[0.18em] text-black/40">
                              <span>{control.confidence_label}</span>
                              <span>
                                {formatPercent(control.confidence * 100)}
                              </span>
                            </div>
                            <Progress
                              value={control.confidence * 100}
                              indicatorClassName={getStatusBarTone(
                                control.status,
                              )}
                            />
                          </div>

                          <div className="text-right text-sm font-medium text-black">
                            {control.findings.length}
                          </div>
                        </div>
                      </button>
                    );
                  })
                ) : (
                  <div className="py-12 text-sm text-black/55">
                    No validation results received yet.
                  </div>
                )}
              </div>
            </div>

            <div className="xl:border-l xl:border-black/10 xl:pl-10">
              <div className="mb-6 flex items-end justify-between gap-4">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.22em] text-black/45">
                    Control detail
                  </p>
                  <p className="mt-2 text-sm text-black/55">
                    Select a control to inspect its reasoning and evidence
                    trail.
                  </p>
                </div>
                {selectedControl ? (
                  <Badge
                    variant={getStatusBadgeVariant(selectedControl.status)}
                  >
                    {selectedControl.status.replace("_", " ")}
                  </Badge>
                ) : null}
              </div>

              {selectedControl ? (
                <div className="animate-detail-enter space-y-8">
                  <div className="space-y-3">
                    <div className="flex flex-wrap items-center gap-3">
                      <p className="text-2xl font-semibold tracking-tight text-black">
                        {selectedControl.regulation_id}
                      </p>
                      {selectedControl.severity ? (
                        <SeverityBadge severity={selectedControl.severity} />
                      ) : null}
                    </div>
                    <p className="text-base leading-7 text-black">
                      {selectedControl.title}
                    </p>
                  </div>

                  <Separator />

                  <div className="space-y-3">
                    <p className="text-[11px] uppercase tracking-[0.22em] text-black/45">
                      Overall reasoning
                    </p>
                    <p className="text-sm leading-7 text-black/70">
                      {selectedControl.overall_reasoning}
                    </p>
                  </div>

                  <Separator />

                  <div className="space-y-4">
                    <div className="flex items-center justify-between gap-4">
                      <p className="text-[11px] uppercase tracking-[0.22em] text-black/45">
                        Findings
                      </p>
                      <span className="text-sm text-black/45">
                        {selectedControl.findings.length} total
                      </span>
                    </div>

                    {selectedControl.findings.map((finding, index) => (
                      <div
                        key={`${selectedControl.regulation_id}-${index}`}
                        className="animate-detail-enter space-y-3 border-b border-black/8 pb-4"
                      >
                        <div className="flex flex-wrap items-center gap-3">
                          <Badge variant={getFindingBadgeVariant(finding.type)}>
                            {finding.type}
                          </Badge>
                          <p className="text-sm font-medium leading-6 text-black">
                            {finding.description}
                          </p>
                        </div>

                        {finding.evidence_ref?.snippet ? (
                          <blockquote className="border-l-2 border-orange-500/50 pl-4 text-sm leading-6 text-black/60">
                            &quot;{finding.evidence_ref.snippet}&quot;
                          </blockquote>
                        ) : selectedControl.status === "NO_EVIDENCE" ? (
                          <p className="text-sm leading-6 text-black/45">
                            No direct evidence reference was returned for this
                            control.
                          </p>
                        ) : null}

                        <p className="text-sm leading-6 text-black/60">
                          {finding.reasoning}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="py-12 text-sm text-black/55">
                  Run a review to inspect control-level reasoning.
                </div>
              )}
            </div>
          </div>

          <Separator />

          <div className="py-8">
            <button
              type="button"
              onClick={() => setShowRawOutput((prev) => !prev)}
              className="flex w-full items-center justify-between gap-4 border-b border-black/10 pb-4 text-left"
            >
              <div>
                <p className="text-[11px] uppercase tracking-[0.22em] text-black/45">
                  Raw validation output
                </p>
                <p className="mt-2 text-sm text-black/55">
                  Keep the original structured payload available for audit and
                  debugging.
                </p>
              </div>
              <ChevronDown
                className={`h-4 w-4 text-black/45 transition-transform duration-200 ${
                  showRawOutput ? "rotate-180" : ""
                }`}
              />
            </button>

            {showRawOutput ? (
              <pre className="animate-detail-enter mt-5 overflow-x-auto text-xs leading-6 text-black/60">
                {rawValidationJson || "No validation payload captured yet."}
              </pre>
            ) : null}
          </div>
        </div>
      </section>
    </main>
  );
}
