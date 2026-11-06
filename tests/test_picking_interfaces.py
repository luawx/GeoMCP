from geomcp.mcp.registry import build_registry


def test_picking_tools_are_strict_and_server_fixed():
    registry = build_registry()
    for name in ('backends', 'presets', 'inspect', 'prepare', 'validate', 'run', 'result', 'import'):
        tool = registry.get('picking.' + name)
        assert tool.input_schema['additionalProperties'] is False
        assert 'config_dir' not in tool.input_schema['properties']
    result = registry.get('picking.result')
    assert result.input_schema['properties']['preview_limit']['maximum'] == 100
import asyncio
import json

from geomcp.cli.main import main
from geomcp.models import ok


def test_picking_strict_rejections():
    r = build_registry()
    for payload in ({'job_id': 'j', 'preview_limit': True}, {'job_id': 'j', 'preview_limit': 101},
                    {'job_id': 'j', 'config_dir': 'evil'}):
        assert not r.get('picking.result').handler(**payload)['success']
    response = r.get('picking.prepare').handler(waveform_manifest_ref='w', geometry_ref='g',
        preset_id='p', preset_version='1', overrides={'algorithm': {'command': 'evil'}})
    assert response['error_code'] == 'INVALID_ARGUMENT'


def test_cli_request_and_server_config(monkeypatch, capsys, tmp_path):
    from geomcp.api import picking
    calls = []
    monkeypatch.setattr(picking, 'prepare', lambda **kwargs: calls.append(kwargs) or ok({'prepared_ref': 'p'}))
    request = {'waveform_manifest_ref': 'w', 'geometry_ref': 'g', 'preset_id': 'p', 'preset_version': '1'}
    assert main(['--config-dir', str(tmp_path), 'picking', 'prepare', '--request', json.dumps(request), '--json']) == 0
    assert calls[0] == {**request, 'config_dir': str(tmp_path.resolve())}
    assert json.loads(capsys.readouterr().out)['success']
    assert main(['picking', 'prepare', '--request', '[]', '--json']) == 2


def test_picking_response_budget(monkeypatch):
    from geomcp.api import picking
    monkeypatch.setattr(picking, 'backends', lambda **kwargs: ok({'huge': 'x' * 65536}))
    assert build_registry().get('picking.backends').handler()['error_code'] == 'RESPONSE_TOO_LARGE'


def test_transport_advertises_strict_schemas_and_preserves_arguments():
    from geomcp.mcp.server import create_server
    server = create_server()
    tools = asyncio.run(server.list_tools())
    tool = next(t for t in tools if t.name == 'picking.prepare')
    assert tool.input_schema == build_registry().get('picking.prepare').input_schema
    response = asyncio.run(server.call_tool('picking.result', {'job_id': 'j', 'config_dir': 'evil'}))
    assert response.structured_content['error_code'] == 'INVALID_ARGUMENT'
