export function isStaleVersion(knownVersion: number, currentVersion: number): boolean {
  return knownVersion < currentVersion;
}

export function nextEncounterVersion(currentVersion: number): number {
  return currentVersion + 1;
}
