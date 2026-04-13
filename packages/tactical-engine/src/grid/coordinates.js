export function coordinateKey({ x, y }) {
    return `${x},${y}`;
}
export function isSameCoordinate(a, b) {
    return a.x === b.x && a.y === b.y;
}
export function chebyshevDistance(a, b) {
    return Math.max(Math.abs(a.x - b.x), Math.abs(a.y - b.y));
}
export function manhattanDistance(a, b) {
    return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
}
