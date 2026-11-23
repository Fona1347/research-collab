# Maintenance and deployment

## One source per Skill

Edit skills/<skill-name>, not an installation or a ZIP. Keep shared collection
tooling outside the packages. Retain each component's established tests and
contracts; versions are independent, with pending collection changes under Unreleased.

The collection CLI requires Python 3.11+. validate checks package identity,
required files and Markdown links; it is not a claim of scientific correctness.
scripts/validate.py runs existing component suites and reports every step and log.
Use --component to rerun only an affected group. It never downloads dependencies.

## Build

package supports repeated --skill or all components by default. --output must name
a ZIP. Existing identical output is reusable; different output is never overwritten.
--dry-run writes nothing. ZIP entries are reproducible for the same source revision,
include per-Skill licenses, and are verified against manifest.json before publication.
Local settings, caches and private Mapper profiles are excluded.

Every Skill has an explicit distribution.json file list. Review new runtime resources
before adding them; unlisted source files and missing listed files block publication.
Do not auto-populate it from a directory containing private notes. The inventory
itself is included automatically. File filters are not a content/secret scanner;
inspect the diff and package before publishing.

## Adopt an existing installation

First compare current source and installed files. Preserve meaningful local changes
in the canonical source or leave that component blocked. A reviewed --baseline file
has this shape (real absolute paths and hashes belong in ignored local storage):

    {
      "paper-deep-reading": {
        "path": "<absolute-skills-directory>/paper-deep-reading",
        "files": {"SKILL.md": "<sha256-of-reviewed-installed-file>"}
      }
    }

Include every existing file that the package will replace. The installer binds this
baseline to the exact target and rechecks hashes before writing. A stale baseline
cannot authorize a later edit. Do not create a baseline merely to bypass an unknown
difference. The nine-component migration keeps a complete original inventory and
installation backups in ignored .local/migration.

Use install --skills-root PATH --baseline FILE --dry-run, review its changes, then
run the same command without --dry-run. Backups default to .local/install-backups;
--backup-root can select another explicit directory outside the target.

Subsequent updates use .research-collab-install.json. It records the source revision,
managed paths and hashes. Source-snapshot or working-tree labels are explicit when
a clean committed source is unavailable. Unknown files and config/local.json remain
unmanaged. Only previously managed, unchanged obsolete files can be removed.

## Recovery

A write failure restores changed files and the previous receipt automatically.
Successful updates report the exact backup directory. To revert a successful update:

    python scripts/skills.py restore --backup <reported-backup-directory> --skills-root <original-skills-directory> --dry-run
    python scripts/skills.py restore --backup <reported-backup-directory> --skills-root <original-skills-directory>

Restoration binds the backup to the explicitly named original target and verifies
manifest file closure, backup hashes and receipt ownership before writing. It refuses
to overwrite edits made after the recorded installation. Legitimate older backups
remain usable; the new target argument is required for them too.
check compares managed files and the receipt to the current source, leaving unknown
files alone. It does not claim that external services or scientific results work.

## Runtime settings

The optional lookup MinerU adapter reads config/local.json (or its documented
environment overrides) for the existing Python executable and wrapper script.
The experimental acquisition Skill reads its own config/local.json for tools_root
and protected_root. Copy the component's local.example.json deliberately and use
absolute paths. Do not put API keys or passwords in these files.

Publishing preserves these files; it does not write global environment variables,
install packages, register servers, alter user-level junctions or update plugins.

## Tests and local history

By default the Mapper suite creates synthetic legacy inputs. It does not discover
history by walking to an ancestor AGENTS.md. Set MAPPER_LEGACY_WORKSPACE to an
explicit local material root containing legacy-runs/<run-id>/ to exercise the
original historical assertions and hash checks. The two fixture IDs are listed in
the Mapper baseline. Prepare unchanged local copies under that layout; keep their
original locations and the copies outside public commits. History-specific cases
are skipped when those inputs are not supplied;
other compatibility checks use the synthetic fixtures. Keep --output-dir inside
the explicit workspace when exercising local history, in a separate test directory.
Logs distinguish synthetic coverage from actual historical verification.

Sci-Plot tests must use the package's src tree with the selected interpreter, not an
editable installation from an archived project. The full acquisition runtime smoke
uses configured external executables only for --help and guards; live retrieval is
not part of validation. Its portable guard tests use fake local executables.

## Migration and releases

Old repositories retain their history, stashes and uncommitted changes. Migration
pointer files identify this repository as the future development location.
Changes are committed on a task branch and reviewed by PR. Push that branch for
review; merging and publishing a Release are separate actions. No force push is needed.

## Coverage and limits

See [compatibility](compatibility.md) for component groups, runtime requirements,
legacy behavior and CI scope. The default runner includes Quick and Presentation
behavioral tests and same-repository canonical API integration. The
[semantic cases](evaluation/README.md) require an independent answer and rubric
review; mechanical checks never certify scientific claims or live services.
