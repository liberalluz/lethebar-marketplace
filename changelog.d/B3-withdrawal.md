# B3 - Withdrawal and liveness show on the list

### Added

- A withdrawn version stays on the list with a `withdrawn` label and keeps its
  metadata page; the page has no download link.
- Liveness labels come from the registry's review notes: `unreviewed` when a
  record has no note, `not checked since <date>` when the note is more than six
  months older than the newest review in the index.

### Changed

- `group()` no longer hides withdrawn records; published versions sort before
  withdrawn ones within a collection.

## present

- `changelog.d/B3-withdrawal.md` — Added the withdrawn and liveness labels.
