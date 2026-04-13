export type ParseResult<T> =
  | { ok: true; value: T }
  | { ok: false; error: string };

export const parseNullableNumber = (
  input: string | number | null | undefined,
  errorMessage: string
): ParseResult<number | null> => {
  if (input === null || typeof input === "undefined") {
    return { ok: true, value: null };
  }
  if (typeof input === "number") {
    return Number.isFinite(input)
      ? { ok: true, value: input }
      : { ok: false, error: errorMessage };
  }
  const trimmed = input.trim();
  if (!trimmed) {
    return { ok: true, value: null };
  }
  const value = Number(trimmed);
  return Number.isFinite(value)
    ? { ok: true, value }
    : { ok: false, error: errorMessage };
};

export const parseNullableInt = (
  input: string | number | null | undefined,
  errorMessage: string
): ParseResult<number | null> => {
  const result = parseNullableNumber(input, errorMessage);
  if (!result.ok) {
    return result;
  }
  if (result.value === null) {
    return result;
  }
  return Number.isInteger(result.value)
    ? result
    : { ok: false, error: errorMessage };
};
