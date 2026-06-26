import { type ControlValidation, type StreamEvent, type ValidationFinding } from "@/lib/types";

/* ============================================================
   Stream parsing helpers — preserved verbatim from the original
   app. The backend streams server-sent events ("data: {json}\n\n")
   to /api/stream; these helpers tolerate the various shapes the
   validation payload can arrive in.
   ============================================================ */

export function formatFrontendErrorMessage(message: string) {
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

export function normalizeValidationPayload(payload: unknown): ControlValidation[] {
  return collectValidationCandidates(payload)
    .map(parseControlValidation)
    .filter((item): item is ControlValidation => Boolean(item));
}

/* ------------------------------------------------------------
   Request payload sent to POST /api/stream.
   ------------------------------------------------------------ */
export type ReviewRequest = {
  framework: string;
  category: string;
  source_code_categories: string[];
  repo_owner: string;
  repo_name: string;
};

/* Callbacks the consumer wires into UI state. */
export type StreamHandlers = {
  onStatus?: (message: string | undefined) => void;
  onToken?: (token: string) => void;
  onUpdate?: (results: ControlValidation[]) => void;
  onError?: (message: string) => void;
  onDone?: () => void;
};

export function resolveApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
}

/* ============================================================
   runComplianceStream — fetches the SSE stream and dispatches
   parsed events to the provided handlers. Preserves the original
   page.tsx control flow (status / token / update / done / error).
   ============================================================ */
export async function runComplianceStream(
  request: ReviewRequest,
  handlers: StreamHandlers,
  signal?: AbortSignal,
) {
  const apiBaseUrl = resolveApiBaseUrl();

  const response = await fetch(`${apiBaseUrl}/api/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
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
  let buffer = "";
  let runCompleted = false;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const event of events) {
      const trimmed = event.trim();
      if (!trimmed || !trimmed.startsWith("data: ")) continue;

      const jsonString = trimmed.replace("data: ", "");
      const data: StreamEvent = JSON.parse(jsonString);

      if (data.type === "status") {
        const statusMessage =
          data.message ?? (typeof data.data === "string" ? data.data : data.data?.message);
        handlers.onStatus?.(statusMessage);
      } else if (data.type === "token") {
        handlers.onToken?.(data.token);
      } else if (data.type === "error") {
        handlers.onError?.(data.message);
        return;
      } else if (data.type === "update" || data.type === "updates") {
        handlers.onUpdate?.(normalizeValidationPayload(data.data));
      } else if (data.type === "done") {
        runCompleted = true;
        handlers.onDone?.();
        return;
      }
    }
  }

  if (!runCompleted) {
    throw new Error("The compliance run ended before a completion event was received.");
  }
}
