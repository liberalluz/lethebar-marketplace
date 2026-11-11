import type { Index, Pack } from "./registry.js";
import { descriptorUrl, releaseUrl } from "./links.js";

export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export interface Group {
  collection: string;
  packs: Pack[];
}

function compare(a: Pack, b: Pack): number {
  return a.id === b.id
    ? a.version.localeCompare(b.version)
    : a.id.localeCompare(b.id);
}

export function group(packs: Pack[]): Group[] {
  const buckets = new Map<string, Pack[]>();
  for (const pack of packs) {
    if (pack.status === "withdrawn") continue;
    const key = pack.collection ?? "Other";
    const list = buckets.get(key) ?? [];
    list.push(pack);
    buckets.set(key, list);
  }
  const names = [...buckets.keys()].sort((a, b) => {
    if (a === "Other") return 1;
    if (b === "Other") return -1;
    return a.localeCompare(b);
  });
  return names.map((name) => ({
    collection: name,
    packs: (buckets.get(name) ?? []).sort(compare),
  }));
}

export function kindLabel(pack: Pack): string {
  return pack.kind === "layer" ? `layer: ${pack.layer ?? ""}` : "bundle";
}

export function packagePath(pack: Pack): string {
  return `p/${pack.namespace}/${pack.id}/${pack.version}.html`;
}

function page(title: string, body: string): string {
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeHtml(title)}</title>
<style>
body{font:16px/1.5 system-ui,sans-serif;max-width:52rem;margin:2rem auto;padding:0 1rem;color:#111}
h1{font-size:1.6rem}h2{font-size:1.2rem;margin-top:2rem}
ul{padding-left:1.2rem}.version,.kind{color:#555;font-size:.9rem;margin-left:.4rem}
table{border-collapse:collapse}td,th{text-align:left;padding:.2rem .8rem .2rem 0;vertical-align:top}
.warn{background:#fff4e5;border-left:4px solid #d97706;padding:.6rem 1rem;margin:1rem 0}
</style>
</head>
<body>
${body}
</body>
</html>
`;
}

export function renderIndex(index: Index): string {
  const groups = group(index.packages);
  const sections = groups
    .map(
      (g) => `<section>
<h2>${escapeHtml(g.collection)}</h2>
<ul>
${g.packs
  .map(
    (p) =>
      `<li><a href="${escapeHtml(packagePath(p))}">${escapeHtml(p.id)}</a> <span class="version">${escapeHtml(p.version)}</span> <span class="kind">${escapeHtml(kindLabel(p))}</span></li>`,
  )
  .join("\n")}
</ul>
</section>`,
    )
    .join("\n");
  return page(
    "Lethebar marketplace",
    `<h1>Packages</h1>
<p>Everything here is a record in the registry. A download leaves for the author's release.</p>
${sections || "<p>No packages yet.</p>"}`,
  );
}

export function renderPackage(pack: Pack): string {
  const withdrawn =
    pack.status === "withdrawn"
      ? `<p class="warn">Withdrawn: this version is no longer offered. The record stays for anyone who installed it.</p>`
      : "";
  return page(
    `${pack.id} ${pack.version}`,
    `<h1>${escapeHtml(pack.id)} <span class="version">${escapeHtml(pack.version)}</span></h1>
${withdrawn}
<table>
<tr><th>kind</th><td>${escapeHtml(kindLabel(pack))}</td></tr>
<tr><th>collection</th><td>${escapeHtml(pack.collection ?? "Other")}</td></tr>
<tr><th>author</th><td>${escapeHtml(pack.author)}</td></tr>
<tr><th>license</th><td>${escapeHtml(pack.license)}</td></tr>
<tr><th>spec</th><td>${escapeHtml(pack.specVersion)}</td></tr>
<tr><th>engine</th><td>${escapeHtml(pack.engine)}</td></tr>
<tr><th>sha256</th><td><code>${escapeHtml(pack.sha256)}</code></td></tr>
<tr><th>capabilities</th><td>${pack.capabilities.map((c) => `<code>${escapeHtml(c)}</code>`).join(" ")}</td></tr>
</table>
<p><a href="${escapeHtml(releaseUrl(pack))}">Download ${escapeHtml(pack.id)}-${escapeHtml(pack.version)}.zip</a>
 · <a href="${escapeHtml(descriptorUrl(pack))}">descriptor</a></p>`,
  );
}
