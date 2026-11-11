export type Kind = "bundle" | "layer";
export type Status = "published" | "withdrawn";

export interface Pack {
  namespace: string;
  id: string;
  version: string;
  sha256: string;
  specVersion: string;
  engine: string;
  capabilities: string[];
  author: string;
  license: string;
  homepage: string;
  tags: string[];
  collection?: string;
  kind: Kind;
  layer?: string;
  publishedAt: string;
  status: Status;
}

export interface Index {
  schemaVersion: number;
  generatedAt: string;
  packages: Pack[];
}

const REQUIRED = [
  "namespace",
  "id",
  "version",
  "sha256",
  "specVersion",
  "engine",
  "capabilities",
  "author",
  "license",
  "homepage",
  "tags",
  "kind",
  "publishedAt",
  "status",
] as const;

export function parseIndex(text: string, where = "index.json"): Index {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(`${where}: not JSON`);
  }
  if (typeof data !== "object" || data === null) {
    throw new Error(`${where}: not an object`);
  }
  const obj = data as {
    schemaVersion?: unknown;
    generatedAt?: unknown;
    packages?: unknown;
  };
  if (typeof obj.schemaVersion !== "number") {
    throw new Error(`${where}: no schemaVersion`);
  }
  if (!Array.isArray(obj.packages)) {
    throw new Error(`${where}: no packages array`);
  }
  const packages = obj.packages.map((raw, i) => {
    if (typeof raw !== "object" || raw === null) {
      throw new Error(`${where}: record ${i} is not an object`);
    }
    const pack = raw as Record<string, unknown>;
    for (const key of REQUIRED) {
      if (pack[key] === undefined || pack[key] === null) {
        throw new Error(
          `${where}: record ${i} (${String(pack.id ?? "?")}) has no ${key}`,
        );
      }
    }
    if (pack.kind !== "bundle" && pack.kind !== "layer") {
      throw new Error(
        `${where}: record ${i} (${String(pack.id)}) has kind ${String(pack.kind)}`,
      );
    }
    if (pack.kind === "layer" && typeof pack.layer !== "string") {
      throw new Error(`${where}: layer ${String(pack.id)} has no layer name`);
    }
    if (pack.status !== "published" && pack.status !== "withdrawn") {
      throw new Error(
        `${where}: record ${i} (${String(pack.id)}) has status ${String(pack.status)}`,
      );
    }
    return pack as unknown as Pack;
  });
  return {
    schemaVersion: obj.schemaVersion,
    generatedAt: String(obj.generatedAt ?? ""),
    packages,
  };
}
