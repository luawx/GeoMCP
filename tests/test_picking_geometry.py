import json
import pytest
from geomcp.scientific.picking.contracts import validate_geometry
from geomcp.exceptions import ScientificToolError


def test_geometry_rejects_crs(tmp_path):
    path = tmp_path / 'geometry.json'
    path.write_text(json.dumps({'schema_version':'1.0', 'geometry_id':'g', 'crs':'EPSG:3857'}))
    with pytest.raises(ScientificToolError, match='CRS'):
        validate_geometry(path, lambda p: p, {'max_input_bytes':10000,'max_receivers':10})
