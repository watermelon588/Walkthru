---
name: walkthru-ai-visibility
description: Read Walkthru AI answer tracking, summarize brand mentions and supported citations, set up tracking for an authorized site, change tracked prompts or competitors, and request a new provider batch. Use for questions about how configured AI engines name or cite a site and what the latest batch measured.
compatibility: Requires Walkthru Plus and its remote MCP connection. Engine availability and quotas depend on the connected deployment.
---

# Walkthru AI Visibility

See [setup](../../shared/setup.md) and the [AI answers tool reference](../../shared/mcp-tools.md#ai-answers). Use the launch reports skill for a saved GEO readiness audit of a site's pages.

1. Use `list_ai_answer_sites` to find the tracked site when the user has not provided its exact address. Use `get_ai_answers` to read the latest batch. If the site is untracked, explain the setup path and wait for a request to enable it.
2. To start tracking, call `track_ai_answers` when the user explicitly asks to track their site. Use the requested brand and competitors when supplied. Show the initial prompt list returned by Walkthru.
3. To change prompts, competitors or the brand, read the current settings first. Use `set_ai_prompts` with only fields the user wants changed. A supplied list replaces the previous list. When asked to add an item, preserve the other entries in the replacement list.
4. Call `check_ai_answers_now` only when the user requests a fresh check. Show how many answers were queued. Read results with `get_ai_answers` when available and give the user the pending status if provider capacity delays completion.

Report the configured engines, prompt and batch scope, completed and pending counts, brand mentions, and citations where measurable. Keep a name match separate from a verified source citation, especially if another business uses the same name. Qualify share of voice as a measure of the sampled answers. Use the engine labels returned by Walkthru and report unmeasured surfaces as such. This pack uses Walkthru's configured data sources.
