from geomcp.config import GeoMCPConfig
from geomcp.exceptions import ConfigurationError


def test_loads_all_configuration(config_dir):
    config = GeoMCPConfig.load(config_dir)
    assert config.section("geomcp")["project"]["name"] == "GeoMCP-Test"


def test_rejects_unsafe_capability(config_dir):
    path = config_dir / "permissions.yaml"
    path.write_text(path.read_text().replace("delete: false", "delete: true"), encoding="utf-8")
    try:
        GeoMCPConfig.load(config_dir)
    except ConfigurationError as exc:
        assert "Unsafe capabilities" in str(exc)
    else:
        raise AssertionError("unsafe capability must fail closed")
