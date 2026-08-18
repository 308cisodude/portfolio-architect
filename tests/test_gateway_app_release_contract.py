"""Static release contract for the native Home Assistant App."""

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
APP = ROOT / "home_assistant_app" / "portfolio_architect_gateway"


def test_app_config_is_private_and_least_privilege() -> None:
    config = yaml.safe_load((APP / "config.yaml").read_text(encoding="utf-8"))
    assert config["version"] == "1.34.0"
    assert config["slug"] == "portfolio_architect_gateway"
    assert config["startup"] == "services"
    assert config["ingress"] is True
    assert config["ingress_port"] == 8099
    assert config["ingress_stream"] is False
    assert config["panel_admin"] is True
    assert config["host_network"] is False
    assert config["hassio_api"] is False
    assert config["homeassistant_api"] is False
    assert config["auth_api"] is False
    assert config["docker_api"] is False
    assert config["apparmor"] is True
    assert config["ports"]["8787/tcp"] is None
    forbidden = {"username", "password", "client_id", "client_secret", "token"}
    assert not forbidden.intersection(config["options"])
    assert not forbidden.intersection(config["schema"])


def test_app_image_and_runtime_contract() -> None:
    dockerfile = (APP / "Dockerfile").read_text(encoding="utf-8")
    entrypoint = (APP / "entrypoint.py").read_text(encoding="utf-8")
    assert "python:3.14.6-alpine3.24@sha256:" in dockerfile
    assert 'io.hass.version="${BUILD_VERSION}"' in dockerfile
    assert 'io.hass.type="app"' in dockerfile
    assert 'io.hass.arch="${BUILD_ARCH}"' in dockerfile
    assert "ARG BUILD_VERSION=1.34.0" in dockerfile
    assert "AppOptions.load" in entrypoint
    assert "os.setgid(APP_GID)" in entrypoint
    assert "os.setuid(APP_UID)" in entrypoint
    assert not (APP / "apparmor.txt").exists()


def test_app_brand_assets_are_present() -> None:
    from PIL import Image
    with Image.open(APP / "icon.png") as icon:
        assert icon.format == "PNG"
        assert icon.size == (128, 128)
    with Image.open(APP / "logo.png") as logo:
        assert logo.format == "PNG"
        assert logo.size == (250, 100)


def test_app_source_matches_gateway_source() -> None:
    gateway_source = ROOT / "gateway" / "src" / "portfolio_architect_gateway"
    app_source = APP / "src" / "portfolio_architect_gateway"
    gateway_files = sorted(path.name for path in gateway_source.glob("*.py"))
    app_files = sorted(path.name for path in app_source.glob("*.py"))
    assert app_files == gateway_files
    for name in gateway_files:
        assert (app_source / name).read_bytes() == (gateway_source / name).read_bytes()


def test_integration_defaults_to_local_app_hostname() -> None:
    const = (ROOT / "custom_components" / "portfolio_architect" / "const.py").read_text(encoding="utf-8")
    assert "https://local-portfolio-architect-gateway:8787/api/v1/portfolio" in const
