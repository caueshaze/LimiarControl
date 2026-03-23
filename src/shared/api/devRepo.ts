import { http } from "./http";

export type DevScriptRun = {
  script: string;
  ok: boolean;
  exitCode: number;
  stdoutTail?: string | null;
  stderrTail?: string | null;
};

export type DevSyncBaseCsvsResponse = {
  ok: boolean;
  message: string;
  scripts: DevScriptRun[];
};

export const devRepo = {
  syncBaseCsvs: () => http.post<DevSyncBaseCsvsResponse>("/dev/sync-base-csvs", {}),
};
