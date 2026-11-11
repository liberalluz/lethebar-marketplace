import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { parseIndex } from "./registry.js";
import { readReviews } from "./liveness.js";
import { packagePath, renderIndex, renderPackage } from "./pages.js";

function fail(message: string): never {
  console.error(message);
  process.exit(1);
}

const here = process.cwd();
const registryDir = resolve(
  here,
  process.env.REGISTRY_DIR ?? join("..", "..", "lethebar-marketplace-registry"),
);
const indexPath = join(registryDir, "index.json");

let text: string;
try {
  text = readFileSync(indexPath, "utf8");
} catch {
  fail(`cannot read ${indexPath}; set REGISTRY_DIR to a registry checkout`);
}

const index = parseIndex(text, indexPath);
const live = readReviews(registryDir);
const dist = join(here, "dist");
rmSync(dist, { recursive: true, force: true });
mkdirSync(dist, { recursive: true });
writeFileSync(join(dist, "index.html"), renderIndex(index, live));
for (const pack of index.packages) {
  const target = join(dist, packagePath(pack));
  mkdirSync(dirname(target), { recursive: true });
  writeFileSync(target, renderPackage(pack, live));
}
console.log(
  `built ${index.packages.length} record(s) from ${indexPath}; newest review ${live.newest || "none"}`,
);
