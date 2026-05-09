const consumedCampaignEvents = new Map<string, number | string>();

export const consumeCampaignEvent = ({
  scope,
  eventType,
  sessionId,
  version,
}: {
  eventType: string;
  scope: string;
  sessionId?: string | null;
  version?: number;
}) => {
  const key = `${scope}:${eventType}:${sessionId ?? ""}`;

  if (typeof version === "number") {
    const previous = consumedCampaignEvents.get(key);
    if (typeof previous === "number" && previous >= version) {
      return false;
    }
    consumedCampaignEvents.set(key, version);
    return true;
  }

  const fingerprint = sessionId ?? eventType;
  if (consumedCampaignEvents.get(key) === fingerprint) {
    return false;
  }
  consumedCampaignEvents.set(key, fingerprint);
  return true;
};
