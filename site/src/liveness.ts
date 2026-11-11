import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

export interface Liveness {
  /** The newest `reviewed:` date seen in the registry, `""` when there are none. */
  newest: string;
  /** `namespace/id/version` to the date the bytes were last checked. */
  reviewed: Map<string, string>;
}

export function reviewKey(
  namespace: string,
  id: string,
  version: string,
): string {
  return `${namespace}/${id}/${version}`;
}

function readDate(file: string): string {
  const text = readFileSync(file, "utf8");
  const match = /^\s*-?\s*reviewed:\s*(\d{4}-\d{2}-\d{2})\s*$/m.exec(text);
  return match ? match[1] : "";
}

/**
 * Reads the registry's review notes. A note is one file per record:
 * `reviews/<namespace>/<id>/<version>.md`. Missing directories are not an
 * error: a build without the notes simply has no liveness labels.
 */
export function readReviews(registryDir: string): Liveness {
  const root = join(registryDir, "reviews");
  const reviewed = new Map<string, string>();
  if (!existsSync(root)) return { newest: "", reviewed };

  for (const ns of readdirSync(root, { withFileTypes: true })) {
    if (!ns.isDirectory()) continue;
    const nsDir = join(root, ns.name);
    for (const id of readdirSync(nsDir, { withFileTypes: true })) {
      if (!id.isDirectory()) continue;
      const idDir = join(nsDir, id.name);
      for (const file of readdirSync(idDir, { withFileTypes: true })) {
        if (!file.isFile() || !file.name.endsWith(".md")) continue;
        const version = file.name.slice(0, -3);
        const date = readDate(join(idDir, file.name));
        if (date) reviewed.set(reviewKey(ns.name, id.name, version), date);
      }
    }
  }

  const dates = [...reviewed.values()].sort();
  return { newest: dates.at(-1) ?? "", reviewed };
}

/**
 * A record is stale when its note is more than `days` older than the newest
 * review in the index — a data-relative measure, so the same registry commit
 * builds the same pages on any day.
 */
export function staleLabel(
  live: Liveness,
  namespace: string,
  id: string,
  version: string,
  days = 180,
): string {
  const reviewed = live.reviewed.get(reviewKey(namespace, id, version));
  if (!reviewed) return "unreviewed";
  if (!live.newest) return "";
  const age = (Date.parse(live.newest) - Date.parse(reviewed)) / 86_400_000;
  return age > days ? `not checked since ${reviewed}` : "";
}
