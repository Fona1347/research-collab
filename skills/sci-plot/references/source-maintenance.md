# Upstream maintenance

The manifest upstream/sources.toml separates four states:

1. Approved immutable ref used as the compatibility baseline.
2. Latest ref observed remotely.
3. Local adapter status.
4. Runtime package version actually installed.

source status reads only the local manifest. source check calls GitHub's read-only API
and prints commit, tag, release, watched-file, and risk summaries. It does not write unless
--record is explicit. Recording updates only observation metadata.

An installed wheel's packaged manifest is an immutable baseline. Recording or approval
must target an explicit writable review copy; this prevents maintenance commands from
rewriting package resources in place. Run source status to locate the packaged
baseline, copy it once to a new workspace-owned review file without overwriting an
existing file, and then use:

    source --manifest WRITABLE_SOURCES_TOML check --record
    source --manifest WRITABLE_SOURCES_TOML update --source ID --ref SHA --approve --tests-passed

source update --source ID --ref REF --approve --tests-passed is deliberately an
approval transaction, not a package manager. The --tests-passed flag is an explicit
attestation that the isolated compatibility and smoke suite passed; it does not run
or install an upstream candidate. Approval succeeds only when REF exactly matches a
recorded latest ref. The before/after audit entry is stored in the same atomically
replaced manifest, with a secondary JSONL audit copy when writable. Installing
pubfig, changing a dependency constraint, or adapting code remains a separate
reviewed repository change with tests. This boundary prevents an automated upstream
change from modifying a working environment or silently changing plot semantics.

If a check reports dependency, spec/CLI, export, or routing changes, inspect the
watched files and run the full Sci Plot smoke suite before approval.
