# GeoMCP Agent Rules

Use GeoMCP as the server-side research interface when a registered GeoMCP tool exists.

- Never request or construct arbitrary shell commands through GeoMCP.
- Never request arbitrary SSH execution through GeoMCP.
- Never delete server files through GeoMCP.
- Do not access paths outside configured read roots.
- Treat raw research data as read-only.
- When project-specific input/output is needed, call `workspace.list` first and use a configured workspace instead of inventing a path region.
- When `workspace` is supplied, use relative paths only; never combine a workspace with an absolute path or `../` traversal.
- Use Job Manager for long-running registered work; cancellation never means deletion.
- Never connect directly to the GPU worker node. GPU work must go through the fixed GeoMCP executor endpoint.
- Never attempt to set GPU host, port, username, remote command, or CUDA environment through tool arguments.

## DAS workflow

1. If the user wants a specific project input/output area, call `workspace.list` and select the configured region.
2. Call `das.inspect` before processing a DAS file.
3. Confirm sampling rate, channel/sample counts, time metadata and data shape.
4. Request the smallest practical channel/sample window; do not read a whole large DAS file without need.
5. For bandpass, keep `0 < freqmin < freqmax < sampling_rate/2`.
6. Write plots/processed arrays only to the selected workspace write root or another GeoMCP-approved output path.
7. Prefer `das.rms` or `das.plot` over returning large raw windows when a summary/visual is sufficient.

Workspace discovery tool: `workspace.list`.

Current DAS Basic tools: `das.inspect`, `das.read_window`, `das.bandpass`, `das.rms`, `das.plot`. Advanced FK/beamforming/denoising belongs to later steps.

## Picking workflow

Discover workspace.list, picking.backends and picking.presets. Inspect inputs,
prepare the exact preset version, validate the returned prepared_ref, then run.
Use job.status/job.cancel and picking.result for lifecycle and artifact references.
Use picking.import for external CSV with explicit column/phase mappings.
Never pass commands, config_dir, model paths or executor selection. Never map
unknown to P/S implicitly. Previews default to 20 and cannot exceed 100. Model
weights are not downloaded. Real-data benchmarks remain required for scientific
acceptance even when interfaces and synthetic tests pass.
