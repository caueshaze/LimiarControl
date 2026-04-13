export function isDiagonalStep(from, to) {
    return Math.abs(from.x - to.x) === 1 && Math.abs(from.y - to.y) === 1;
}
export function stepCost(from, to, diagonalIndex, cellMultiplier = 1) {
    const baseCost = isDiagonalStep(from, to) ? (diagonalIndex % 2 === 0 ? 5 : 10) : 5;
    return baseCost * cellMultiplier;
}
export function computePathCost(path, getMultiplier) {
    let total = 0;
    let diagonalIndex = 0;
    for (let index = 1; index < path.length; index += 1) {
        const dest = path[index];
        const multiplier = getMultiplier ? getMultiplier(dest) : 1;
        const cost = stepCost(path[index - 1], dest, diagonalIndex, multiplier);
        total += cost;
        if (isDiagonalStep(path[index - 1], dest)) {
            diagonalIndex += 1;
        }
    }
    return total;
}
