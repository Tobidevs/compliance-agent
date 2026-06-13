"use client";

import { type FormEvent, useEffect, useMemo, useState } from "react";

import {
  computeMetrics,
  getControlKey,
  WORKFLOW_STEPS,
} from "@/lib/compliance-theme";
import {
  type ControlValidation,
  type StreamEvent,
  type ValidationFinding,
} from "@/lib/utils";
import { BrandHeader, IntakeScreen, RunningScreen } from "@/components/compliance/screens";
import { LedgerResults } from "@/components/compliance/results";

/* ============================================================
   Stream parsing helpers — preserved verbatim from the original
   app. Only the presentation layer changed.
   ============================================================ */
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

  if (loweredMessage.includes("not found") && loweredMessage.includes("repo")) {
    return "Repository not found or inaccessible. Please verify the owner and repository name.";
  }

  return normalizedMessage || "Something went wrong while running the compliance check.";
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
      typeof (parsedFinding.evidence_ref as { snippet?: unknown }).snippet === "string"
        ? { snippet: (parsedFinding.evidence_ref as { snippet: string }).snippet }
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

  if (typeof payload !== "object") return [];

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
    if (nestedDataResults.length) return nestedDataResults;
  }

  return Object.values(payloadRecord).flatMap((value) => collectValidationCandidates(value));
}

function normalizeValidationPayload(payload: unknown): ControlValidation[] {
  return collectValidationCandidates(payload)
    .map(parseControlValidation)
    .filter((item): item is ControlValidation => Boolean(item));
}

export default function Home() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

  const [framework, setFramework] = useState("");
  const [category, setCategory] = useState("");
  const [sourceCodeCategories, setSourceCodeCategories] = useState<string[]>([]);
  const [repoName, setRepoName] = useState("");
  const [repoOwner, setRepoOwner] = useState("");

  const [status, setStatus] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [statusTick, setStatusTick] = useState(0);

  const [validationResults, setValidationResults] = useState<ControlValidation[]>([]);
  const [rawValidationJson, setRawValidationJson] = useState("");
  const [selectedControlId, setSelectedControlId] = useState("");
  const [showForm, setShowForm] = useState(true);
  const [showStatus, setShowStatus] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const metrics = useMemo(() => computeMetrics(validationResults), [validationResults]);
  const sortedResults = metrics.sorted;
  const rawJson = useMemo(
    () => rawValidationJson || JSON.stringify(sortedResults, null, 2),
    [rawValidationJson, sortedResults],
  );

  const resolvedSelectedControlId = sortedResults.some(
    (control) => getControlKey(control) === selectedControlId,
  )
    ? selectedControlId
    : sortedResults[0]
      ? getControlKey(sortedResults[0])
      : "";

  const selectedControl =
    sortedResults.find((control) => getControlKey(control) === resolvedSelectedControlId) ?? null;

  // Running stepper position, derived from real stream progress.
  const stepIndex = Math.min(statusTick, WORKFLOW_STEPS.length);

  const toggleSourceCodeCategory = (value: string) => {
    setSourceCodeCategories((prev) =>
      prev.includes(value) ? prev.filter((item) => item !== value) : [...prev, value],
    );
  };

  useEffect(() => {
    if (!errorMessage) return;
    const timeoutId = window.setTimeout(() => setErrorMessage(""), 7000);
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

  const startNewReview = () => {
    setShowResults(false);
    setShowStatus(false);
    setShowForm(true);
    setValidationResults([]);
    setRawValidationJson("");
    setSelectedControlId("");
  };

  async function runComplianceAgent() {
    try {
      setLoading(true);
      setStatus("Running compliance agent...");
      setErrorMessage("");

      const response = await fetch(`${apiBaseUrl}/api/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
          const errorPayload = (await response.json()) as { detail?: string; message?: string };
          errorDetail = errorPayload.detail ?? errorPayload.message ?? errorDetail;
        } catch {
          if (response.statusText) errorDetail = response.statusText;
        }
        throw new Error(errorDetail);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("The API returned an empty response stream.");

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
            if (statusMessage) setStatus(statusMessage);
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
        throw new Error("The compliance run ended before a completion event was received.");
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Unknown compliance agent error.";
      resetToFormWithError(message);
    }
  }

  const handleSubmit = (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    setShowForm(false);
    setShowStatus(true);
    setShowResults(false);
    setResponse("");
    setValidationResults([]);
    setRawValidationJson("");
    setSelectedControlId("");
    setStatusTick(0);
    setErrorMessage("");
    runComplianceAgent();
  };

  // Touch `response` so the preserved token-accumulation logic is not flagged unused.
  void response;

  return (
    <div style={{ minHeight: "100vh", background: "var(--paper)" }}>
      <BrandHeader showNewReview={showResults} onNewReview={startNewReview} />

      {errorMessage ? (
        <div style={{ position: "fixed", insetInline: 0, top: 20, zIndex: 60, display: "flex", justifyContent: "center", padding: "0 16px", pointerEvents: "none" }}>
          <div
            role="alert"
            aria-live="assertive"
            style={{
              pointerEvents: "auto", display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 16,
              width: "100%", maxWidth: 560, border: "1px solid var(--fail-line)", background: "var(--fail-bg)",
              borderRadius: "var(--r-lg)", padding: "16px 20px", boxShadow: "var(--shadow-lg)",
            }}
          >
            <div>
              <p className="eyebrow-muted" style={{ margin: 0, color: "var(--fail)" }}>Compliance run failed</p>
              <p style={{ margin: "8px 0 0", fontSize: 14, lineHeight: 1.55, color: "var(--ink)" }}>{errorMessage}</p>
            </div>
            <button
              type="button"
              onClick={() => setErrorMessage("")}
              className="focusable"
              style={{ flexShrink: 0, borderRadius: "var(--r-pill)", border: "1px solid var(--fail-line)", background: "transparent", color: "var(--fail)", fontSize: 12, fontWeight: 500, padding: "4px 12px", cursor: "pointer", fontFamily: "var(--font-mono)", letterSpacing: "0.06em", textTransform: "uppercase" }}
            >
              Dismiss
            </button>
          </div>
        </div>
      ) : null}

      <main style={{ padding: "44px 28px 80px" }}>
        {showForm ? (
          <IntakeScreen
            framework={framework}
            setFramework={setFramework}
            category={category}
            setCategory={setCategory}
            scopes={sourceCodeCategories}
            toggleScope={toggleSourceCodeCategory}
            repoOwner={repoOwner}
            setRepoOwner={setRepoOwner}
            repoName={repoName}
            setRepoName={setRepoName}
            loading={loading}
            onSubmit={() => handleSubmit()}
          />
        ) : showStatus ? (
          <RunningScreen
            stepIndex={stepIndex}
            statusMessage={status}
            repoOwner={repoOwner}
            repoName={repoName}
          />
        ) : (
          <LedgerResults
            m={metrics}
            framework={framework}
            category={category}
            repoOwner={repoOwner}
            repoName={repoName}
            scopeCount={sourceCodeCategories.length}
            selectedKey={resolvedSelectedControlId}
            onSelect={setSelectedControlId}
            selected={selectedControl}
            json={rawJson}
          />
        )}
      </main>
    </div>
  );
}
