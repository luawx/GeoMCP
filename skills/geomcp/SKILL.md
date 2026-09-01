# GeoMCP Agent Rules

Use GeoMCP as the only server-side research tool interface when a registered GeoMCP tool exists.

- Never request or construct arbitrary shell commands through GeoMCP.
- Never request arbitrary SSH execution through GeoMCP.
- Do not delete server files.
- Do not access paths outside the configured read roots.
- Treat raw research data as read-only.
- Do not download complete large DAS datasets to the client; inspect metadata or process server-side.
- When Job Manager is available, use it for long-running work.
- Do not connect directly to the GPU worker node; future GPU work must be dispatched through GeoMCP.
