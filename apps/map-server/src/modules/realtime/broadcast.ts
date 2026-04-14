import {
  integrationSpatialEventEnvelopeSchema,
  type IntegrationSpatialEventEnvelope
} from "@limiarmap/shared-contracts";
import { CentrifugoPublisher } from "./centrifugo-publisher";

export interface BroadcastAdapter {
  emit(eventName: string, payload: unknown): void;
}

export interface SpatialEventPublisher {
  publish(channel: string, data: IntegrationSpatialEventEnvelope): Promise<void> | void;
}

export const MAP_SYSTEM_EVENTS_CHANNEL = "system:map_events";
export const MAP_LEGACY_EVENTS_CHANNEL = "session:map_events";

const centrifugo: SpatialEventPublisher = new CentrifugoPublisher();

export function getSpatialEventChannels(encounterId: string): string[] {
  return [`session:${encounterId}`, MAP_SYSTEM_EVENTS_CHANNEL, MAP_LEGACY_EVENTS_CHANNEL];
}

export function broadcastAuthoritativeEvent(
  broadcaster: BroadcastAdapter | undefined,
  eventName: string,
  payload: unknown,
  publisher: SpatialEventPublisher = centrifugo
): void {
  broadcaster?.emit(eventName, payload);

  const parsed = integrationSpatialEventEnvelopeSchema.safeParse(payload);
  if (!parsed.success) {
    console.warn(
      `[realtime] skipping Centrifugo publish for invalid authoritative event ${eventName}`,
      parsed.error.flatten()
    );
    return;
  }

  const envelope = parsed.data;
  if (envelope.eventType !== eventName) {
    console.warn(
      `[realtime] authoritative event type mismatch socketEvent=${eventName} envelopeEvent=${envelope.eventType}`
    );
  }

  if (process.env.VITEST && publisher === centrifugo) {
    return;
  }

  for (const channel of getSpatialEventChannels(envelope.encounterId)) {
    try {
      void publisher.publish(channel, envelope);
    } catch (error) {
      console.error(
        `[realtime] failed to dispatch authoritative event ${eventName} to channel ${channel}:`,
        error
      );
    }
  }
}
