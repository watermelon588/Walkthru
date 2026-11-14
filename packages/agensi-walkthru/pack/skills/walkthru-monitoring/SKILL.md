---
name: walkthru-monitoring
description: Manage Walkthru weekly site watch, read monitoring changes, request a post-deploy check, create or rotate a deploy webhook, discover connected GitHub repositories, and preview or open a configuration-fix pull request from a Walkthru report.
compatibility: Requires Walkthru Plus and its remote MCP connection. Pull requests require the Walkthru GitHub App to be configured and installed for the repository.
---

# Walkthru Monitoring

See [setup](../../shared/setup.md) and the [monitoring and GitHub tool reference](../../shared/mcp-tools.md#watch-and-github). Use the launch reports skill to read a saved report or draft a general fix plan.

## Weekly and deploy checks

1. Use `list_watched_sites` to show what's monitored, recent changes and next check dates. Use the exact site returned when requesting another action.
2. Use `watch_site` only when the user explicitly wants ongoing monitoring for a site they control or are authorized to monitor. Explain that enabling it starts a baseline, schedules future checks and can notify the owner when findings change.
3. For an explicitly requested immediate check of a watched site, call `check_watched_site_now`. If the server reports a cooldown, surface it. Report pending work and read changes from `list_watched_sites` when ready.
4. Before calling `create_deploy_hook`, confirm the site and explain that creating a hook replaces the previous URL. The returned URL is a secret and shown once. The user should store it in the approved deploy service's private webhook or CI secret settings. Keep it out of chat summaries, files, pull requests and logs. If the agent has no approved private destination, direct the owner to create and copy the URL through Walkthru settings instead.

## Configuration-fix pull requests

1. Call `list_github_repos` to confirm the repository and integration status. Use `get_report` or `list_runs` from the shared tool reference when the user needs help identifying the report. Confirm that the report belongs to the site the repository deploys.
2. Call `open_fix_pull_request` with `confirm=false`. Show the repository, target branch, file list and changes left for the user. If the GitHub App is unavailable, use `get_fix_prompt` for a manual fix plan.
3. Open the pull request with `confirm=true` only after the user approves that specific preview for that repository. Return the link and summarize what the tool changed. The owner reviews and merges it in GitHub.
