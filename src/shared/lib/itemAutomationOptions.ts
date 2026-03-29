const dedupePreservingOrder = (values: readonly string[]) => {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const value of values) {
    if (seen.has(value)) {
      continue;
    }
    seen.add(value);
    result.push(value);
  }
  return result;
};

export const AUTOMATION_DICE_OPTIONS = [
  "1",
  "1d4",
  "1d6",
  "1d8",
  "1d10",
  "1d12",
  "2d4",
  "2d6",
  "2d8",
  "2d10",
  "2d12",
  "3d4",
  "3d6",
  "4d4",
  "4d6",
  "8d4",
  "10d4",
] as const;

export const AUTOMATION_RANGE_OPTIONS = [
  "1",
  "2",
  "3",
  "4",
  "5",
  "6",
  "9",
  "10",
  "12",
  "15",
  "18",
  "20",
  "24",
  "30",
  "36",
  "45",
  "60",
  "90",
  "120",
  "150",
  "180",
  "300",
  "600",
] as const;

export const AUTOMATION_ARMOR_CLASS_OPTIONS = [
  "10",
  "11",
  "12",
  "13",
  "14",
  "15",
  "16",
  "17",
  "18",
  "19",
  "20",
  "21",
  "22",
  "23",
  "24",
  "25",
] as const;

export const AUTOMATION_HEAL_BONUS_OPTIONS = [
  "0",
  "1",
  "2",
  "3",
  "4",
  "5",
  "6",
  "7",
  "8",
  "9",
  "10",
  "12",
  "15",
  "20",
] as const;

export const AUTOMATION_STRENGTH_REQUIREMENT_OPTIONS = [
  "8",
  "9",
  "10",
  "11",
  "12",
  "13",
  "14",
  "15",
  "16",
  "17",
  "18",
  "19",
  "20",
] as const;

export const buildAutomationSelectOptions = (
  value: string,
  options: readonly string[],
) => {
  const normalized = value.trim();
  if (!normalized) {
    return ["", ...options];
  }
  return dedupePreservingOrder(["", normalized, ...options]);
};
