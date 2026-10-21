export function parseCsv(text: string): string[][] {
  const rows: string[][] = []; let row: string[] = []; let cell = ""; let q = false;
  text = text.replace(/^\uFEFF/, "");
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (q) {
      if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += ch;
    } else if (ch === '"') q = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n" || ch === "\r") { if (ch === "\r" && text[i + 1] === "\n") i++; row.push(cell); rows.push(row); row = []; cell = ""; }
    else cell += ch;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows.filter((r) => r.some((c) => c.trim()));
}

/** Parse into objects keyed by header (case-insensitive lookups via lowercased keys). */
export function csvObjects(text: string): { header: string[]; rows: Record<string, string>[] } {
  const all = parseCsv(text);
  if (!all.length) return { header: [], rows: [] };
  const header = all[0].map((h) => h.trim());
  return { header, rows: all.slice(1).map((r) => Object.fromEntries(header.map((h, i) => [h.toLowerCase(), (r[i] ?? "").trim()]))) };
}

export function downloadText(name: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
  const a = document.createElement("a"); a.href = url; a.download = name; a.click(); URL.revokeObjectURL(url);
}
