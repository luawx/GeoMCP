# GeoMCP Agent Skill

Use GeoMCP through registered MCP tools instead of constructing ad-hoc remote commands.

## Safety rules

- Do not directly SSH to GPU node 1015 for scientific work; GPU dispatch belongs to later Worker/Executor steps.
- Do not request arbitrary shell commands, arbitrary SSH commands, executable paths, file deletion, or recursive deletion.
- Do not access paths outside configured read roots.
- Treat raw research data as read-only. Writes are allowed only under configured GeoMCP output/runtime/knowledge roots.
- Inspect or window large DAS datasets rather than copying entire datasets into the agent context.
- Once Job Manager exists, submit long-running work as jobs rather than blocking an MCP request.

## Available tools after Step 05

- `system.status`: inspect GeoMCP status.
- `filesystem.inspect`: inspect file/directory metadata after sandbox validation.
