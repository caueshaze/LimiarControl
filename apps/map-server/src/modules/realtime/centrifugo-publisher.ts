export interface CentrifugoConfig {
  apiUrl: string;
  apiKey: string;
}

export class CentrifugoPublisher {
  private overrides: Partial<CentrifugoConfig>;

  constructor(config?: Partial<CentrifugoConfig>) {
    this.overrides = config ?? {};
  }

  private resolveConfig(): CentrifugoConfig {
    return {
      apiUrl: this.overrides.apiUrl ?? process.env.CENTRIFUGO_API_URL ?? "http://localhost:8001/api",
      apiKey: this.overrides.apiKey ?? process.env.CENTRIFUGO_API_KEY ?? "dev-api-key",
    };
  }

  public async publish(channel: string, data: unknown): Promise<void> {
    const config = this.resolveConfig();
    try {
      const response = await fetch(`${config.apiUrl}/publish`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": config.apiKey,
        },
        body: JSON.stringify({
          channel,
          data,
        }),
      });

      if (!response.ok) {
        throw new Error(`Centrifugo publish failed: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error(`[Centrifugo] Failed to publish down channel ${channel}:`, error);
    }
  }
}
