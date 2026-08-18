"""Branding and copyable instrument identifier contracts."""

from pathlib import Path
import json
import yaml
from PIL import Image

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "portfolio_architect"


def test_local_integration_brand_assets() -> None:
    brand = INTEGRATION / "brand"
    expected = {
        "icon.png": (128, 128),
        "dark_icon.png": (128, 128),
        "icon@2x.png": (256, 256),
        "dark_icon@2x.png": (256, 256),
        "logo.png": (250, 100),
        "dark_logo.png": (250, 100),
        "logo@2x.png": (500, 200),
        "dark_logo@2x.png": (500, 200),
    }
    for filename, size in expected.items():
        with Image.open(brand / filename) as image:
            assert image.format == "PNG"
            assert image.size == size


def test_proposed_purchase_identifiers_have_labels() -> None:
    for language in ("en", "de"):
        data = json.loads((INTEGRATION / "translations" / f"{language}.json").read_text(encoding="utf-8"))
        attrs = data["entity"]["sensor"]["proposed_buy"]["state_attributes"]
        assert attrs["fund_name"]["name"]
        assert attrs["isin"]["name"] == "ISIN"
        assert attrs["wkn"]["name"] == "WKN"


def test_proposed_purchase_identity_attributes_are_first() -> None:
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    block = source[source.index('class PortfolioProposedBuySensor'):source.index('class _PortfolioPlanScheduleDateSensor')]
    assert block.index('"fund_name"') < block.index('"isin"') < block.index('"wkn"') < block.index('"fund_id"')


def test_copyable_isin_entity_and_dashboard_actions() -> None:
    source = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
    assert "class PortfolioInstrumentIsinSensor" in source
    assert 'return f"{self._fund_id}_isin"' in source
    plan = yaml.safe_load((ROOT / "examples/current-plan/portfolio.yaml").read_text(encoding="utf-8"))
    target_ids = [item["target_id"] for item in plan["portfolio"]["allocation"]]
    for dashboard in (ROOT / "dashboard").rglob("*.yaml"):
        text = dashboard.read_text(encoding="utf-8")
        for target_id in target_ids:
            if f"sensor.portfolio_architect_{target_id}_proposed_buy" not in text:
                continue
            assert f"entity: sensor.portfolio_architect_{target_id}_isin" in text

