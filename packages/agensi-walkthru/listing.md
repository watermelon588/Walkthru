# Walkthru Launch Toolkit on Agensi

**Price** Free  
**Needs access to** Walkthru MCP for connected workflows  
**Version** 0.1.0

## Summary

Review Walkthru reports, plan fixes, check AI search visibility and manage site monitoring from your agent. Import an existing report or connect your Walkthru Plus account for live access to your reports and tools.

## Description

**Connected features require an existing Walkthru Plus account and a personal API key.** You can also supply a Walkthru report or findings export for review without connecting an account.

- **Launch Reports** explains what Walkthru measured, prioritizes fixes, and helps review saved runs, passive technical checks, comparisons, finding status and usage.
- **AI Visibility** reads tracked answer batches, distinguishes mentions from supported citations, and manages prompts and checks on the configured engines.
- **Monitoring** reviews weekly checks and deploy changes, helps set up a deploy webhook, and previews configuration fixes for a connected GitHub repository.

Connect to Walkthru from your agent using the setup example. Live work uses your Walkthru account's permissions and limits. Browser journeys start in the Walkthru Chrome extension. GitHub pull requests require the Walkthru GitHub App to be configured and connected.

## Compatibility

An agent client connected to Agensi. Connected features also require a separate Streamable HTTP MCP connection with a custom Authorization header. The ZIP contains a Cursor configuration example and setup instructions for other compatible clients.

## Example to show

The ZIP includes a [fictional report walkthrough](pack/shared/example.md). Use a recorded request and result in the marketplace demo field when one is available.

## Upload

Upload `walkthru-agensi-skill-pack.zip` via [Agensi Creator Studio](https://www.agensi.io/dashboard/submit). The editable archive contents live in `pack/`. To rebuild the ZIP after editing, run `python -m zipfile -c walkthru-agensi-skill-pack.zip pack/README.md pack/shared pack/skills` from this directory.
