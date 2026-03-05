export type Session = {
  id: string;
  campaignId: string;
  number: number;
  title: string;

  status?: "LOBBY" | "ACTIVE" | "CLOSED";
  isActive?: boolean;
  startedAt?: string | null;
  endedAt?: string | null;
  durationSeconds?: number;
  createdAt: string;
  updatedAt?: string | null;
};
