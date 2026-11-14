---
name: walkthru-launch-reports
description: Review Walkthru reports and findings exports, explain browser journey evidence, prioritize fixes, run passive technical checks on authorized sites, compare sites, manage finding status, share reports, check domain ownership, and explain Walkthru usage or journey quotes. Use when the user asks what Walkthru found, what to fix, or how to verify a fix.
compatibility: Report import works from supplied text or a CSV the agent can read. Connected actions require Walkthru Plus and its remote MCP connection.
---

# Walkthru Launch Reports

Read the [tool reference](../../shared/mcp-tools.md) for inputs and [setup](../../shared/setup.md) if the Walkthru connection is missing. Use the dedicated AI visibility skill for tracked AI answer batches. Use the monitoring skill for weekly checks, deploy hooks and GitHub pull requests.

## Review a report

1. If the user supplied a report, CSV or fix prompt, work from that input. Ask for the relevant excerpt if the file cannot be read or lacks the needed evidence.
2. For connected reports, use the supplied run ID or call `list_runs`. Match the returned site and the requested run type. If several reports match and the choice matters, ask the user which one to use. Pick the most recent matching report for requests that specify “latest.”
3. Call `get_report` and use the chapter index to retrieve the requested scope. Follow the returned cursor for a complete chapter only when needed. Use `get_finding` with an ID from the report for a focused evidence review. Use `get_fix_prompt` for the existing Markdown fix plan, optionally scoped to a chapter.
4. Present the report date, site and what Walkthru measured. Give each priority item an affected page or step, the evidence, the proposed change and a way to verify it. Use “not measured,” “pending” or “ended early” when supported by the result. Preserve uncertainty about the cause or outcome. A completed scan does not establish whether a browser journey worked.

## Scan, compare or recheck

Use `scan_site` only for an explicitly requested passive check on a site the user owns or is authorized to assess. Use `compare_sites` for an explicitly requested comparison of authorized public targets. Keep it to the requested URLs and report the returned run ID as queued until `get_report` shows a result. These actions use the account's scan allowance. Keep security guidance defensive and grounded in reported hygiene findings.

For a requested retest of an earlier technical report, use `rerun`. For one technical finding, use `verify_finding` and relay the exact result, including checks that could not be repeated. For browser journey verification, guide the user to repeat the goal in the Chrome extension and review the saved report afterward.

## Account, ownership and report changes

- Use `get_plan` for allowances and included features. Use `get_usage` for the recorded work ledger, with `get_plan` as the fallback for remaining runs. Use `get_run_quote` when the user asks what a journey would use. The quote is informational. The user starts the journey from the Chrome extension.
- Use `get_site_verification` for a site the user controls. Give the exact verification option the server supplies. The user publishes the proof, then Walkthru can check the live site again.
- Call `accept_finding` only for an explicit owner decision and reason. Call `reopen_finding` only when the user wants the accepted finding restored. Use the exact report and finding ID.
- Before `share_report`, confirm the exact report and that the user wants anyone with its link to be able to read it. Return the link and badge after the server confirms sharing.
