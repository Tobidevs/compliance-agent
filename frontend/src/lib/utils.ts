import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type StreamEvent =
  | {
      type: "status";
      message: string;
    }
  | {
      type: "token";
      token: string;
    }
  | {
      type: "update";
      data: any;
    }
  | {
      type: "updates";
      data: any;
    }
  | {
      type: "done";
    }
  | {
      type: "error";
      message: string;
    };
