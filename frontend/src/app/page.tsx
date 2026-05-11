"use client";

import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StreamEvent } from "@/lib/utils";

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

  const [validationResults, setValidationResults] = useState("");
  const [showForm, setShowForm] = useState(true);
  const [showStatus, setShowStatus] = useState(false);
  const [showResults, setShowResults] = useState(false);

  const normalizeValidationPayload = (payload: unknown) => {
    if (!payload) return payload;
    const asRecord = payload as Record<string, unknown>;
    let results =
      typeof payload === "object" && "validation_results" in asRecord
        ? asRecord.validation_results
        : payload;

    if (Array.isArray(results)) {
      results = results.flatMap((item) => (Array.isArray(item) ? item : [item]));
    }

    return results;
  };

  const toggleSourceCodeCategory = (value: string) => {
    setSourceCodeCategories((prev) =>
      prev.includes(value)
        ? prev.filter((item) => item !== value)
        : [...prev, value],
    );
  };

  async function runComplianceAgent() {
    try {
      setLoading(true);
      setStatus("Running compliance agent...");

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
        throw new Error(`Error: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder("utf-8");
      let result = "";

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;
        result += decoder.decode(value, { stream: true });
        const events = result.split("\n\n");

        result = events.pop() || "";

        for (const event of events) {
          const trimmed = event.trim();
          if (!trimmed) continue;
          if (!trimmed.startsWith("data: ")) continue;

          const jsonString = trimmed.replace("data: ", "");
          const data: StreamEvent = JSON.parse(jsonString);

          console.log("STREAM EVENT:", data);
          if (data.type === "status") {
            const statusMessage =
              (data as { message?: string }).message ??
              (typeof (data as { data?: unknown }).data === "string"
                ? (data as { data?: string }).data
                : (data as { data?: { message?: string } }).data?.message);
            if (statusMessage) {
              setStatus(statusMessage);
            }
            setStatusTick((prev) => prev + 1);
          } else if (data.type === "token") {
            setResponse((prev) => prev + data.token);
          } else if (data.type === "error") {
            setStatus(`Error: ${data.message}`);
            setStatusTick((prev) => prev + 1);
            setLoading(false);
            setShowStatus(true);
            setShowResults(false);
            return;
          } else if (data.type === "update" || data.type === "updates") {
            const normalized = normalizeValidationPayload(data.data);
            setValidationResults(JSON.stringify(normalized, null, 2));
          } else if (data.type === "done") {
            setStatus("Compliance agent run complete.");
            setStatusTick((prev) => prev + 1);
            setLoading(false);
            setShowStatus(false);
            setTimeout(() => setShowResults(true), 250);
            return;
          }
        }
      }
      setLoading(false);
    } catch (error: any) {
      setStatus(`Error: ${error.message}`);
      setStatusTick((prev) => prev + 1);
      setLoading(false);
      setShowStatus(true);
      setShowResults(false);
    }
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setShowForm(false);
    setShowStatus(true);
    setShowResults(false);
    setResponse("");
    setValidationResults("");
    runComplianceAgent();
  };

  const screenBase =
    "absolute inset-0 overflow-y-auto px-6 py-16 transition-opacity duration-500";
  const screenVisible = "opacity-100 pointer-events-auto";
  const screenHidden = "opacity-0 pointer-events-none";

  return (
    <main className="relative min-h-screen bg-white">
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
            Provide repository details and pick the validation scope. We will use
            these inputs to shape the compliance review.
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
            <div key={statusTick} className="animate-status text-base text-black">
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
        <div className="mx-auto w-full max-w-3xl">
          <div className="text-center">
            <p className="text-xs uppercase tracking-[0.3em] text-orange-500">
              Compliance Validation
            </p>
            <h2 className="mt-4 text-2xl font-semibold text-black sm:text-3xl">
              Validation Results
            </h2>
            <p className="mt-3 text-sm text-black/60">
              Review the final compliance output and findings captured by the
              workflow.
            </p>
          </div>

          <div className="mt-10 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-black/10 bg-white px-5 py-4">
              <p className="text-xs uppercase tracking-[0.2em] text-black/45">
                Framework
              </p>
              <p className="mt-2 text-lg font-medium text-black">
                {framework || "SOC 2"}
              </p>
            </div>
            <div className="rounded-xl border border-black/10 bg-white px-5 py-4">
              <p className="text-xs uppercase tracking-[0.2em] text-black/45">
                Repository
              </p>
              <p className="mt-2 text-lg font-medium text-black">
                {repoOwner && repoName
                  ? `${repoOwner}/${repoName}`
                  : "Repository not provided"}
              </p>
            </div>
            <div className="rounded-xl border border-black/10 bg-white px-5 py-4">
              <p className="text-xs uppercase tracking-[0.2em] text-black/45">
                Category
              </p>
              <p className="mt-2 text-lg font-medium text-black">
                {category || "Not specified"}
              </p>
            </div>
            <div className="rounded-xl border border-black/10 bg-white px-5 py-4">
              <p className="text-xs uppercase tracking-[0.2em] text-black/45">
                Source code scopes
              </p>
              <p className="mt-2 text-sm font-medium text-black">
                {sourceCodeCategories.length
                  ? sourceCodeCategories.join(", ")
                  : "Not specified"}
              </p>
            </div>
          </div>

          <div className="mt-8 rounded-2xl border border-black/10 bg-white px-6 py-5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-black">Validation JSON</p>
              <span className="text-xs text-black/45">
                {validationResults ? "Captured" : "Awaiting data"}
              </span>
            </div>
            <pre className="mt-4 max-h-[360px] overflow-auto rounded-lg bg-black/5 p-4 text-xs text-black/70">
              {validationResults || "No validation results received yet."}
            </pre>
          </div>
        </div>
      </section>
    </main>
  );
}
