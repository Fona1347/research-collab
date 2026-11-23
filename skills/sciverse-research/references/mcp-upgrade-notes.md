# Sciverse setup and maintenance

The Skill is a workflow adapter. The Sciverse service, MCP server, account, token,
and historical setup diary are external; installing the Skill does not install or
configure them.

Read sciverse-api.md and sciverse-paper-schema.md for the supported interfaces.
Use sciverse-validation-test.md for a bounded connectivity check only when the
current task requires live retrieval. Preserve source IDs and partial/truncated
state. Resolve the host's actual tool availability before choosing an API route.

Keep credentials in the host's existing secret handling. Never include a token in
a command line, source file, fixture, log, or report. Updating this collection does
not change host MCP registration or upgrade its server.

Historical workspace validation is not evidence that a new installation has a
working service. Missing tools or entitlement remain explicit limitations.
