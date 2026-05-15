import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type EvidenceRef = {
  snippet: string;
};

export type ValidationFinding = {
  type: "violation" | "pass" | "gap";
  description: string;
  evidence_ref?: EvidenceRef | null;
  reasoning: string;
};

export type ControlValidation = {
  regulation_id: string;
  title: string;
  status: "PASS" | "FAIL" | "PARTIAL" | "NO_EVIDENCE";
  severity?: "critical" | "high" | "medium" | "low" | null;
  confidence: number;
  confidence_label: "High" | "Medium" | "Low" | "Inconclusive";
  findings: ValidationFinding[];
  overall_reasoning: string;
};

export type StreamEvent =
  | {
      type: "status";
      message?: string;
      data?: string | { message?: string; type?: string };
    }
  | {
      type: "token";
      token: string;
    }
  | {
      type: "update";
      data: unknown;
    }
  | {
      type: "updates";
      data: unknown;
    }
  | {
      type: "done";
    }
  | {
      type: "error";
      message: string;
    };
