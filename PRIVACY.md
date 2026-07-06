# Privacy

`unlimited-search` runs locally as an MCP server.

By default, it does not operate a hosted service and does not send request logs to the project maintainers.

The tool may fetch:

- URLs provided by the MCP client
- public route variants such as feeds or metadata endpoints
- media metadata through `yt-dlp`

The tool may return fetched page content to the MCP client that invoked it. Treat returned web content as untrusted.

Do not provide credentials, private URLs, tokens, session cookies, or personal data unless you understand where your MCP client sends tool results.
