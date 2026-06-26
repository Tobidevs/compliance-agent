"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { usePathname, useRouter } from "next/navigation";

import { computeMetrics, getControlKey, WORKFLOW_STEPS } from "@/lib/compliance-theme";
import { type ControlValidation } from "@/lib/types";
import {
  formatFrontendErrorMessage,
  runComplianceStream,
  type ReviewRequest,
} from "@/lib/stream";

/* ============================================================
   ReviewProvider — single source of truth for the whole flow:
   intake form state, the live /api/stream run, parsed results,
   selection, explorer search, and route transitions between
   /  (new review) → /run (live) → /results (dashboard).
   Mounted above the router in the root layout so the run survives
   navigation between the three screens.
   ============================================================ */

type ReviewContextValue = {
  // form
  framework: string;
  setFramework: (v: string) => void;
  category: string;
  setCategory: (v: string) => void;
  scopes: string[];
  toggleScope: (v: string) => void;
  repoOwner: string;
  setRepoOwner: (v: string) => void;
  repoName: string;
  setRepoName: (v: string) => void;
  ready: boolean;
  repoLabel: string;

  // run
  loading: boolean;
  status: string;
  stepIndex: number;
  errorMessage: string;
  dismissError: () => void;

  // results
  metrics: ReturnType<typeof computeMetrics>;
  hasResults: boolean;
  rawJson: string;
  selectedKey: string;
  setSelectedKey: (key: string) => void;
  selectedControl: ControlValidation | null;
  search: string;
  setSearch: (v: string) => void;

  // actions
  submitReview: () => void;
  startNewReview: () => void;
};

const ReviewContext = createContext<ReviewContextValue | null>(null);

export function ReviewProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  const [framework, setFramework] = useState("");
  const [category, setCategory] = useState("");
  const [scopes, setScopes] = useState<string[]>([]);
  const [repoOwner, setRepoOwner] = useState("");
  const [repoName, setRepoName] = useState("");

  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [statusTick, setStatusTick] = useState(0);
  const [errorMessage, setErrorMessage] = useState("");

  const [validationResults, setValidationResults] = useState<ControlValidation[]>([]);
  const [rawValidationJson, setRawValidationJson] = useState("");
  const [selectedControlId, setSelectedControlId] = useState("");
  const [search, setSearch] = useState("");

  // Token accumulation is preserved from the original (the backend may emit
  // token events); it is not surfaced in this layout but kept for parity.
  const tokenBufferRef = useRef("");
  const abortRef = useRef<AbortController | null>(null);

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

  const stepIndex = Math.min(statusTick, WORKFLOW_STEPS.length);
  const ready = Boolean(framework && repoOwner && repoName && scopes.length > 0);
  const repoLabel = repoOwner && repoName ? `${repoOwner}/${repoName}` : "No repository set";
  const hasResults = sortedResults.length > 0;

  const toggleScope = useCallback((value: string) => {
    setScopes((prev) =>
      prev.includes(value) ? prev.filter((item) => item !== value) : [...prev, value],
    );
  }, []);

  // Auto-clear transient errors.
  useEffect(() => {
    if (!errorMessage) return;
    const timeoutId = window.setTimeout(() => setErrorMessage(""), 7000);
    return () => window.clearTimeout(timeoutId);
  }, [errorMessage]);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const resetToFormWithError = useCallback(
    (message: string) => {
      const formatted = formatFrontendErrorMessage(message);
      setErrorMessage(formatted);
      setStatus(formatted);
      setLoading(false);
      router.push("/");
    },
    [router],
  );

  const startNewReview = useCallback(() => {
    abortRef.current?.abort();
    setValidationResults([]);
    setRawValidationJson("");
    setSelectedControlId("");
    setSearch("");
    setStatus("");
    setStatusTick(0);
    setLoading(false);
    router.push("/");
  }, [router]);

  const runComplianceAgent = useCallback(
    async (request: ReviewRequest) => {
      const controller = new AbortController();
      abortRef.current?.abort();
      abortRef.current = controller;
      try {
        setLoading(true);
        setStatus("Running compliance agent...");
        setErrorMessage("");
        tokenBufferRef.current = "";

        await runComplianceStream(
          request,
          {
            onStatus: (message) => {
              if (message) setStatus(message);
              setStatusTick((prev) => prev + 1);
            },
            onToken: (token) => {
              tokenBufferRef.current += token;
            },
            onUpdate: (normalized) => {
              setValidationResults(normalized);
              setRawValidationJson(JSON.stringify(normalized, null, 2));
            },
            onError: (message) => {
              resetToFormWithError(message);
            },
            onDone: () => {
              setStatus("Compliance agent run complete.");
              setStatusTick((prev) => prev + 1);
              setLoading(false);
              setTimeout(() => router.push("/results"), 250);
            },
          },
          controller.signal,
        );
      } catch (error: unknown) {
        if (controller.signal.aborted) return;
        const message = error instanceof Error ? error.message : "Unknown compliance agent error.";
        resetToFormWithError(message);
      }
    },
    [resetToFormWithError, router],
  );

  const submitReview = useCallback(() => {
    if (!ready) return;
    setValidationResults([]);
    setRawValidationJson("");
    setSelectedControlId("");
    setStatus("");
    setStatusTick(0);
    setErrorMessage("");
    router.push("/run");
    void runComplianceAgent({
      framework,
      category,
      source_code_categories: scopes,
      repo_owner: repoOwner,
      repo_name: repoName,
    });
  }, [ready, framework, category, scopes, repoOwner, repoName, router, runComplianceAgent]);

  // Keep the URL honest: if the user deep-links to /run or /results without a
  // run in flight or any results, send them back to the form.
  useEffect(() => {
    if (pathname === "/results" && !hasResults && !loading) router.replace("/");
    if (pathname === "/run" && !loading && !hasResults) router.replace("/");
  }, [pathname, hasResults, loading, router]);

  const value: ReviewContextValue = {
    framework,
    setFramework,
    category,
    setCategory,
    scopes,
    toggleScope,
    repoOwner,
    setRepoOwner,
    repoName,
    setRepoName,
    ready,
    repoLabel,
    loading,
    status,
    stepIndex,
    errorMessage,
    dismissError: () => setErrorMessage(""),
    metrics,
    hasResults,
    rawJson,
    selectedKey: resolvedSelectedControlId,
    setSelectedKey: setSelectedControlId,
    selectedControl,
    search,
    setSearch,
    submitReview,
    startNewReview,
  };

  return <ReviewContext.Provider value={value}>{children}</ReviewContext.Provider>;
}

export function useReview() {
  const ctx = useContext(ReviewContext);
  if (!ctx) throw new Error("useReview must be used within ReviewProvider");
  return ctx;
}
