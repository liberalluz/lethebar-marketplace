import assert from "node:assert/strict";
import { test } from "node:test";
import { parseIndex } from "../dist/registry.js";
import { group, renderIndex, renderPackage } from "../dist/pages.js";
import { descriptorUrl, releaseUrl } from "../dist/links.js";
import { staleLabel } from "../dist/liveness.js";

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

test("a withdrawn record stays, after the published ones", () => {
  const index = parseIndex(
    indexOf(
      { ...base, id: "sanguo", version: "1.0.0", collection: "three-kingdoms" },
      {
        ...base,
        id: "gone",
        version: "0.1.0",
        collection: "three-kingdoms",
        status: "withdrawn",
      },
      { ...base, id: "loose", version: "0.1.0" },
    ),
  );
  const groups = group(index.packages);
  assert.deepEqual(
    groups.map((g) => g.collection),
    ["three-kingdoms", "Other"],
  );
  assert.deepEqual(
    groups[0].packs.map((p) => p.id),
    ["sanguo", "gone"],
  );
  const list = renderIndex(index);
  assert.match(list, /gone/);
  assert.match(list, /class="status">withdrawn/);
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

test("a withdrawn page keeps its facts and loses its download", () => {
  const index = parseIndex(
    indexOf(
      { ...base, id: "sanguo", version: "1.0.0", collection: "three-kingdoms" },
      { ...base, id: "gone", version: "0.1.0", status: "withdrawn" },
    ),
  );
  const withdrawnPage = renderPackage(index.packages[1]);
  assert.match(withdrawnPage, /Withdrawn/);
  assert.match(withdrawnPage, /No download/);
  assert.doesNotMatch(withdrawnPage, /releases\/download/);
  const publishedPage = renderPackage(index.packages[0]);
  assert.match(publishedPage, /releases\/download/);
});

test("a note older than six months is stale, a missing note is unreviewed", () => {
  const live = {
    newest: "2026-11-01",
    reviewed: new Map([
      ["liberalluz/fresh/1.0.0", "2026-10-01"],
      ["liberalluz/old/1.0.0", "2025-01-01"],
    ]),
  };
  assert.equal(staleLabel(live, "liberalluz", "fresh", "1.0.0"), "");
  assert.equal(
    staleLabel(live, "liberalluz", "old", "1.0.0"),
    "not checked since 2025-01-01",
  );
  assert.equal(staleLabel(live, "liberalluz", "none", "1.0.0"), "unreviewed");
});
