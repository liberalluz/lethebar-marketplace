import assert from "node:assert/strict";
import { test } from "node:test";
import { parseIndex } from "../dist/registry.js";
import { group, renderIndex, renderPackage } from "../dist/pages.js";
import { descriptorUrl, releaseUrl } from "../dist/links.js";

const base = {
  namespace: "liberalluz",
  sha256: "a".repeat(64),
  specVersion: "2.0.0",
  engine: ">=4.7.0 <5.0.0",
  capabilities: ["text@1"],
  author: "liberalluz",
  license: "Apache-2.0",
  tags: ["x"],
  publishedAt: "2026-11-11T00:00:00Z",
  status: "published",
  kind: "bundle",
  homepage: "https://github.com/liberalluz/sanguo/",
};

function indexOf(...packs) {
  return JSON.stringify({
    schemaVersion: 1,
    generatedAt: "2026-11-11T00:00:00Z",
    packages: packs,
  });
}

test("a missing field names the record and the field", () => {
  const text = indexOf({
    ...base,
    id: "sanguo",
    version: "1.0.0",
    collection: "three-kingdoms",
  });
  assert.throws(() => parseIndex("{}", "x.json"), /no schemaVersion/);
  assert.throws(
    () => parseIndex('{"schemaVersion":1}', "x.json"),
    /no packages array/,
  );
  assert.throws(
    () => parseIndex(text.replace('"license":"Apache-2.0",', ""), "x.json"),
    /has no license/,
  );
});

test("withdrawn records leave the list and Other is last", () => {
  const index = parseIndex(
    indexOf(
      { ...base, id: "sanguo", version: "1.0.0", collection: "three-kingdoms" },
      { ...base, id: "loose", version: "0.1.0" },
      { ...base, id: "gone", version: "0.1.0", status: "withdrawn" },
    ),
  );
  const groups = group(index.packages);
  assert.deepEqual(
    groups.map((g) => g.collection),
    ["three-kingdoms", "Other"],
  );
  assert.deepEqual(
    groups.flatMap((g) => g.packs.map((p) => p.id)),
    ["sanguo", "loose"],
  );
});

test("a download link goes to the author's release, tag and all", () => {
  const pack = parseIndex(
    indexOf({
      ...base,
      id: "sanguo",
      version: "1.0.0",
      collection: "three-kingdoms",
    }),
  ).packages[0];
  assert.equal(
    releaseUrl(pack),
    "https://github.com/liberalluz/sanguo/releases/download/pack/sanguo/v1.0.0/sanguo.zip",
  );
  assert.equal(
    descriptorUrl(pack),
    "https://github.com/liberalluz/sanguo/releases/download/pack/sanguo/v1.0.0/sanguo-1.0.0.json",
  );
});

test("the pages carry the record", () => {
  const index = parseIndex(
    indexOf(
      { ...base, id: "sanguo", version: "1.0.0", collection: "three-kingdoms" },
      { ...base, id: "gone", version: "0.1.0", status: "withdrawn" },
    ),
  );
  const list = renderIndex(index);
  assert.match(list, /three-kingdoms/);
  assert.match(list, /p\/liberalluz\/sanguo\/1\.0\.0\.html/);
  assert.doesNotMatch(list, /gone/);
  const page = renderPackage(index.packages[1]);
  assert.match(page, /Withdrawn/);
});
