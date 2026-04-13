export function traceLine(from, to) {
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const nx = Math.abs(dx);
    const ny = Math.abs(dy);
    const signX = dx > 0 ? 1 : -1;
    const signY = dy > 0 ? 1 : -1;
    if (nx === 0 && ny === 0) {
        return [];
    }
    const result = [];
    let x = from.x;
    let y = from.y;
    let ix = 0;
    let iy = 0;
    while (ix < nx || iy < ny) {
        const decision = (1 + 2 * ix) * ny - (1 + 2 * iy) * nx;
        if (decision === 0) {
            x += signX;
            y += signY;
            ix += 1;
            iy += 1;
        }
        else if (decision < 0) {
            x += signX;
            ix += 1;
        }
        else {
            y += signY;
            iy += 1;
        }
        if (x === to.x && y === to.y) {
            continue;
        }
        result.push({ x, y });
    }
    return result;
}
