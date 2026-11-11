import type { Pack } from "./registry.js";

function base(pack: Pack): string {
  return pack.homepage.replace(/\/+$/, "");
}

export function releaseUrl(pack: Pack): string {
  return `${base(pack)}/releases/download/pack/${pack.id}/v${pack.version}/${pack.id}.zip`;
}

export function descriptorUrl(pack: Pack): string {
  return `${base(pack)}/releases/download/pack/${pack.id}/v${pack.version}/${pack.id}-${pack.version}.json`;
}
