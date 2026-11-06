# Picking source snapshots

These are source-only snapshots from official repositories. Each PROVENANCE.json
records its exact commit, fetched ZIP SHA-256, and SHA-256 for every retained file.
Upstream licenses remain in each tree (ObsPy full license: obspy/obspy/LICENSE.txt).
No nested git repositories, pretrained weights or waveform datasets are included.
Regenerate using `.venv/Scripts/python.exe scripts/fetch_picking_sources.py`.
The script uses fixed commits; network access is installation-only, never inference.

Runtime adapters use only administrator registered local environments and weights.
Model registration keys: python, source_dir, weights, sha256 (absolute filename to
SHA-256 for every checkpoint file), sampling_rate_hz; PhaseNet also components
(ordered three strings). source_dir must contain the matching PROVENANCE.json.
PhaseNet weights is a TensorFlow checkpoint prefix; PhaseNet-DAS weights is a
PyTorch state dict with optional model member. DAS model_kwargs configures the
fixed upstream build_model function; no arbitrary code or command is accepted.

PhaseNet calls upstream normalize (constant per-component centering/std), UNet,
and TensorFlow checkpoint restore. EQNet calls upstream PhaseNetDAS build_model,
whose UNet performs moving normalization, with zero padding to 1024 multiples
(minimum time 2048 for reflection) and crops predictions back to input extent.
Input components must already have the administrator registered physical order.
No implicit sample-rate conversion, physical quantity conversion or GPU fallback.

STA/LTA recurrence reproduces ObsPy recursive_sta_lta_py: squared amplitude,
initial sample skipped, warmup nlta samples; state crosses internal block boundaries
and resets on non-finite samples. Unclosed triggers are rejected. Output time is
trigger opening, score is peak ratio. No P/S classification or uncertainty invented.

The adapters are not scientifically benchmarked. Real weights, independent native
reference fixtures, isolated dependency locks, CPU/GPU resource and scientific
benchmarks are required before production registration. Unit tests do not establish
real-model accuracy or numerical agreement with registered checkpoint predictions.

## Isolated installation and validation

Create separate Python 3.11 virtual environments outside the server environment.
For example, `py -3.11 -m venv D:\GeoMCP-envs\phasenet`, then install with
`D:\GeoMCP-envs\phasenet\Scripts\python.exe -m pip install -r third_party/phasenet-environment.candidate.txt`.
Repeat with the EQNet candidate template in a different environment. Installation
requires network or an administrator prepared offline wheelhouse. Set registered
python to the environment's absolute executable; source_dir points at the retained
snapshot. GPU builds require separately verified platform-specific CUDA wheels.

These candidate templates are review starting points, not verified dependency
locks. PhaseNet upstream pins TensorFlow 2.11; the Python 3.11 candidate instead
uses 2.15.1, the last Keras 2 line preserving its v1 layers. This deviation needs
real-checkpoint regression validation. EQNet upstream leaves torch/torchvision
unpinned; 2.5.1/0.20.1 is a matched candidate pair, not an upstream version claim.
After isolated install and native-reference inference tests, preserve `pip freeze`,
Python/platform details and wheel hashes as the environment fingerprint. Do not
mark either backend production-ready based on a successful package installation.

STA/LTA supports bounded streaming calls: preserve a mutable context.state dictionary,
pass context.offset as cumulative selected-window samples and context.final=true on
the last call. Without state, a call is a complete record. With state, final defaults
false. Candidate sample_index is global relative to the selected-window origin,
even when the closing threshold arrives in a later block. Receiver order and rate
must remain constant. Optional context.diagnostics list receives rejected-trigger
ranges with short_trigger, long_trigger, gap_trigger or unclosed_trigger reasons.

Git attributes preserve snapshot bytes without line-ending conversion. Upstream
whitespace is retained, so vendor snapshots are excluded from Git whitespace checks.
The provenance test verifies retained files against the pinned SHA-256 manifest.
