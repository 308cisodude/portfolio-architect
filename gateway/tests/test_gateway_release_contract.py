import json
from pathlib import Path
import sys

GATEWAY_ROOT = Path(__file__).parents[1]
FULL_ROOT = GATEWAY_ROOT.parent
sys.path.insert(0, str(GATEWAY_ROOT / "src"))

from portfolio_architect_gateway import __version__  # noqa: E402


def test_gateway_and_integration_versions_are_compatible() -> None:
    assert __version__ == "1.56.0"
    component = FULL_ROOT / "custom_components" / "portfolio_architect"
    if component.exists():
        manifest = json.loads((component / "manifest.json").read_text())
        const = (component / "const.py").read_text()
        engine = (component / "engine" / "__init__.py").read_text()
        assert manifest["version"] == "1.56.0"
        assert 'VERSION: Final = "1.56.0"' in const
        assert '__version__ = "1.56.0"' in engine


def test_gateway_package_is_dependency_free() -> None:
    dockerfile = (GATEWAY_ROOT / "Dockerfile").read_text()
    assert "pip install" not in dockerfile
    assert "requirements" not in dockerfile
