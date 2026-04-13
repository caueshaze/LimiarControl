export function isStaleVersion(knownVersion, currentVersion) {
    return knownVersion < currentVersion;
}
export function nextEncounterVersion(currentVersion) {
    return currentVersion + 1;
}
