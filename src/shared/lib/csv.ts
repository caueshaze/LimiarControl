export const parseCsv = (text: string): string[][] => {
  const rows: string[][] = [];
  let currentRow: string[] = [];
  let currentCell = "";
  let insideQuotes = false;
  const input = text.replace(/^\uFEFF/, "");

  const pushCell = () => {
    currentRow.push(currentCell.trim());
    currentCell = "";
  };

  const pushRow = () => {
    if (currentRow.length === 0 && currentCell.trim() === "") {
      currentCell = "";
      return;
    }
    pushCell();
    if (currentRow.some((cell) => cell !== "")) {
      rows.push(currentRow);
    }
    currentRow = [];
  };

  for (let index = 0; index < input.length; index += 1) {
    const char = input[index];
    const next = input[index + 1];

    if (char === '"') {
      if (insideQuotes && next === '"') {
        currentCell += '"';
        index += 1;
      } else {
        insideQuotes = !insideQuotes;
      }
      continue;
    }

    if (!insideQuotes && char === ",") {
      pushCell();
      continue;
    }

    if (!insideQuotes && (char === "\n" || char === "\r")) {
      if (char === "\r" && next === "\n") {
        index += 1;
      }
      pushRow();
      continue;
    }

    currentCell += char;
  }

  if (currentCell !== "" || currentRow.length > 0) {
    pushRow();
  }

  return rows;
};

export const parseCsvObjects = <THeader extends string = string>(
  text: string,
): Record<THeader, string>[] => {
  const [headers = [], ...rows] = parseCsv(text);
  return rows.map((row) => {
    const entry = {} as Record<THeader, string>;
    headers.forEach((header, index) => {
      entry[header as THeader] = row[index] ?? "";
    });
    return entry;
  });
};
