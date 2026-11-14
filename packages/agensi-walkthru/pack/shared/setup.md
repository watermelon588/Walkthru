# Connect Walkthru to your agent

Use [Agensi's connection guide](https://www.agensi.io/docs/connect-your-agent) to load the pack. To review a report you already have, paste the text or attach the Walkthru findings CSV directly in your agent and ask for a fix plan.

## Connect an existing Plus account

1. Sign in to Walkthru. In Settings, open **API keys and MCP** and create a personal key. Walkthru shows the key once. Store it in your agent client's private user settings or secret store.
2. Add a second MCP connection named `walkthru` in the agent client. Use the remote **Streamable HTTP** transport and `https://api.trywalkthru.com/mcp`. Set the `Authorization` header to `Bearer ` followed by your personal Walkthru key.
3. In Cursor, use the [example configuration](walkthru-mcp.example.json) as a template for your user-level MCP settings. Copy the `walkthru` entry into your existing `mcpServers` object. Replace the example value in your private settings. For Claude Code, use the setup instructions shown in Walkthru Settings. For other clients, use the equivalent Streamable HTTP server and header settings.
4. Enable the connection in your client. Ask the agent to use the pack and show your Walkthru plan or list your recent reports.

Agensi sign-in loads the skills. Your Walkthru key authorizes the separate connection from your agent to Walkthru. Keep the key out of chats, example files and shared project settings. Revoke a lost key in Walkthru Settings and update the client with its replacement.

| What you see | What to do |
| --- | --- |
| The agent cannot see Walkthru tools | Check that the separate `walkthru` connection is enabled and supports remote HTTP with a Bearer header. Report import is available for report review. |
| `401` or invalid key | Check the header and key in private client settings. |
| `402` or Plus required | Check the connected Walkthru account's plan. |
| Report not found | Confirm the report is owned by the connected account and select the matching run from `list_runs`. |
| Quota or rate-limit message | Show the server's message and wait for the limit to reset or narrow the request. |
| Feature unavailable | Report the server's response. GitHub, provider usage and scheduled work can depend on deployment configuration. |
