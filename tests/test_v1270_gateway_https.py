"""Regression contracts for v1.27.0 verified Gateway HTTPS transport."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import ssl
import sys
import types

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "portfolio_architect"
GATEWAY_SRC = ROOT / "gateway" / "src"
GATEWAY = GATEWAY_SRC / "portfolio_architect_gateway"
APPS = ROOT / "home_assistant_app"
APP_SLUGS = (
    "portfolio_architect_gateway",
    "portfolio_architect_gateway_dkb",
    "portfolio_architect_gateway_trade_republic",
)


def _load_supervisor_tls():
    sys.path.insert(0, str(GATEWAY_SRC))
    try:
        module = importlib.import_module("portfolio_architect_gateway.supervisor_tls")
        return importlib.reload(module)
    finally:
        try:
            sys.path.remove(str(GATEWAY_SRC))
        except ValueError:
            pass


def _load_rest_client():
    """Load rest_client with only the Home Assistant type boundary stubbed."""
    for name in tuple(sys.modules):
        if name == "custom_components" or name.startswith(
            "custom_components.portfolio_architect"
        ) or name == "homeassistant" or name.startswith("homeassistant."):
            sys.modules.pop(name, None)

    custom_components = types.ModuleType("custom_components")
    custom_components.__path__ = [str(ROOT / "custom_components")]
    package = types.ModuleType("custom_components.portfolio_architect")
    package.__path__ = [str(COMPONENT)]
    sys.modules["custom_components"] = custom_components
    sys.modules["custom_components.portfolio_architect"] = package

    homeassistant = types.ModuleType("homeassistant")
    core = types.ModuleType("homeassistant.core")

    class HomeAssistant:  # pragma: no cover - type placeholder only
        pass

    core.HomeAssistant = HomeAssistant
    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.core"] = core
    return importlib.import_module("custom_components.portfolio_architect.rest_client")


def _generate_tls(tmp_path: Path, hostname: str = "local-portfolio-architect-gateway"):
    tls = _load_supervisor_tls()
    directory = tmp_path / "tls"
    tls._create_initial_material(tmp_path, directory, "comdirect", hostname)
    ca_pem = tls._read_ca_certificate(directory / "ca-cert.pem")
    return tls, directory, ca_pem


def test_official_apps_enable_discovery_and_https_runtime_dependency() -> None:
    for slug in APP_SLUGS:
        app = APPS / slug
        config = yaml.safe_load((app / "config.yaml").read_text(encoding="utf-8"))
        assert config["discovery"] == ["portfolio_architect"]
        assert config["hassio_api"] is False
        assert config["homeassistant_api"] is False
        assert config["ports"]["8787/tcp"] is None
        assert config["watchdog"] == "tcp://[HOST]:[PORT:8787]"
        dockerfile = (app / "Dockerfile").read_text(encoding="utf-8")
        assert "apk add --no-cache openssl=3.5.7-r0" in dockerfile
        entrypoint = (app / "entrypoint.py").read_text(encoding="utf-8")
        assert "prepare_supervisor_tls" in entrypoint
        assert "start_supervisor_tls_discovery_publisher" in entrypoint
        assert "tls_cert_file=tls.cert_file" in entrypoint
        assert "tls_key_file=tls.key_file" in entrypoint

    workflows = {}
    for workflow_name in ("validate.yml", "release.yml"):
        workflow = (ROOT / ".github" / "workflows" / workflow_name).read_text(encoding="utf-8")
        workflows[workflow_name] = workflow
        assert "--network-alias supervisor" in workflow
        assert '--env "SUPERVISOR_TOKEN=${supervisor_token}"' in workflow
        assert 'if self.path != "/addons/self/info"' in workflow
        assert 'if self.path != "/discovery"' in workflow
        assert 'ssl.create_default_context(cafile="/data/gateway/tls/ca-cert.pem")' in workflow

    def smoke_body(workflow: str) -> str:
        start = workflow.index("      - name: Smoke-test provider shell containers\n")
        end = workflow.index("      - name: Scan source, history, and release artifacts for secrets\n", start)
        return workflow[start:end]

    assert smoke_body(workflows["validate.yml"]) == smoke_body(workflows["release.yml"])


def test_private_pki_survives_leaf_renewal_without_changing_trust_anchor(tmp_path: Path) -> None:
    tls, directory, ca_pem = _generate_tls(tmp_path)
    old_fingerprint = tls._certificate_sha256(ca_pem)
    old_ca = (directory / "ca-cert.pem").read_bytes()
    old_ca_key = (directory / "ca-key.pem").read_bytes()

    assert tls._leaf_is_usable(directory, "local-portfolio-architect-gateway")
    tls._renew_leaf(directory, "local-portfolio-architect-gateway-v2")

    assert tls._leaf_is_usable(directory, "local-portfolio-architect-gateway-v2")
    assert (directory / "ca-cert.pem").read_bytes() == old_ca
    assert (directory / "ca-key.pem").read_bytes() == old_ca_key
    assert tls._certificate_sha256(tls._read_ca_certificate(directory / "ca-cert.pem")) == old_fingerprint
    assert (directory / "ca-key.pem").stat().st_mode & 0o777 == 0o600
    assert (directory / "server-key.pem").stat().st_mode & 0o777 == 0o600
    assert directory.stat().st_mode & 0o777 == 0o700


def test_existing_broken_tls_directory_never_silently_resets_ca(tmp_path: Path, monkeypatch) -> None:
    tls = _load_supervisor_tls()
    directory = tmp_path / "tls"
    directory.mkdir(mode=0o700)
    (directory / "ca-cert.pem").write_text("broken", encoding="ascii")
    monkeypatch.setattr(
        tls,
        "_supervisor_json",
        lambda *_args, **_kwargs: {"hostname": "local-portfolio-architect-gateway"},
    )
    before = (directory / "ca-cert.pem").read_bytes()
    with pytest.raises(RuntimeError, match="refusing trust reset"):
        tls.prepare_supervisor_tls(tmp_path, "comdirect", supervisor_token="x" * 32)
    assert (directory / "ca-cert.pem").read_bytes() == before


def test_supervisor_discovery_contains_only_public_tls_identity(tmp_path: Path, monkeypatch) -> None:
    tls, directory, ca_pem = _generate_tls(tmp_path)
    material = tls.SupervisorTlsMaterial(
        hostname="local-portfolio-architect-gateway",
        cert_file=directory / "server-cert.pem",
        key_file=directory / "server-key.pem",
        ca_certificate_pem=ca_pem,
        ca_sha256=tls._certificate_sha256(ca_pem),
    )
    captured: dict[str, object] = {}

    def fake_supervisor(method, path, token, base_url, *, payload=None):
        captured.update({"method": method, "path": path, "token": token, "base_url": base_url, "payload": payload})
        return {"uuid": "a" * 32}

    monkeypatch.setattr(tls, "_supervisor_json", fake_supervisor)
    assert tls.publish_supervisor_tls_discovery(
        material, "comdirect", supervisor_token="supervisor-secret"
    ) == "a" * 32

    payload = captured["payload"]
    assert isinstance(payload, dict)
    serialized = json.dumps(payload, sort_keys=True)
    assert payload["service"] == "portfolio_architect"
    assert payload["config"]["provider_id"] == "comdirect"
    assert payload["config"]["host"] == material.hostname
    assert payload["config"]["ca_certificate"] == ca_pem
    assert payload["config"]["ca_sha256"] == material.ca_sha256
    assert "PRIVATE KEY" not in serialized
    assert "supervisor-secret" not in serialized
    assert "rest_api_token" not in serialized


def test_gateway_tls_discovery_is_strict_and_matches_only_same_network_identity(tmp_path: Path) -> None:
    tls, _directory, ca_pem = _generate_tls(tmp_path)
    rest = _load_rest_client()
    fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert(ca_pem)).hexdigest()
    discovery = rest.GatewayTlsDiscovery.from_mapping(
        {
            "transport_schema_version": 1,
            "provider_id": "comdirect",
            "host": "local-portfolio-architect-gateway",
            "port": 8787,
            "path": "/api/v1/portfolio",
            "ca_certificate": ca_pem,
            "ca_sha256": fingerprint,
        }
    )
    assert discovery.endpoint_url == "https://local-portfolio-architect-gateway:8787/api/v1/portfolio"
    assert discovery.matches_legacy_endpoint(
        "http://local-portfolio-architect-gateway:8787/api/v1/portfolio"
    )
    assert not discovery.matches_legacy_endpoint(
        "http://other-gateway:8787/api/v1/portfolio"
    )
    assert not discovery.matches_legacy_endpoint(
        "http://local-portfolio-architect-gateway:8788/api/v1/portfolio"
    )
    with pytest.raises(rest.PortfolioRestTlsError):
        rest.GatewayTlsDiscovery.from_mapping(
            {
                "transport_schema_version": 1,
                "provider_id": "comdirect",
                "host": "local-portfolio-architect-gateway",
                "port": 8787,
                "path": "/api/v1/portfolio",
                "ca_certificate": ca_pem,
                "ca_sha256": "0" * 64,
            }
        )


def test_rest_transport_uses_verified_hostname_checking_and_private_ca_only(tmp_path: Path, monkeypatch) -> None:
    _tls, _directory, ca_pem = _generate_tls(tmp_path)
    rest = _load_rest_client()
    config = rest.RestSourceConfig(
        "https://local-portfolio-architect-gateway:8787/api/v1/portfolio",
        "x" * 32,
        ca_pem,
    )
    default_called = False
    original_default = ssl.create_default_context

    def track_default(*args, **kwargs):
        nonlocal default_called
        default_called = True
        return original_default(*args, **kwargs)

    monkeypatch.setattr(ssl, "create_default_context", track_default)
    context = rest._rest_ssl_context(config)
    assert context is not None
    assert context.check_hostname is True
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.minimum_version >= ssl.TLSVersion.TLSv1_2
    assert default_called is False

    with pytest.raises(rest.PortfolioRestError):
        rest._rest_ssl_context(
            rest.RestSourceConfig(
                "http://local-portfolio-architect-gateway:8787/api/v1/portfolio",
                "x" * 32,
                ca_pem,
            )
        )


def test_config_flow_migrates_only_after_verified_https_health_and_never_replaces_changed_trust() -> None:
    source = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    init_source = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
    const_source = (COMPONENT / "const.py").read_text(encoding="utf-8")
    rest_source = (COMPONENT / "rest_client.py").read_text(encoding="utf-8")

    assert "VERSION = 9" in source
    assert "if entry.version > 9:" in init_source
    assert "if entry.version < 9:" in init_source
    assert "async def async_step_hassio" in source
    assert "async def async_step_hassio_add_supplemental_confirm" in source
    assert 'reason="tls_supplemental_added"' in source
    assert 'reason="tls_trust_changed"' in source
    assert 'reason="tls_migrated"' in source
    # Any already-HTTPS source is an established trust decision: only an
    # identical discovered CA is a no-op; every other trust root is refused.
    assert source.count('return self.async_abort(reason="tls_trust_changed")') >= 2
    assert "system-PKI trust decision" in source
    assert "health = await async_fetch_gateway_health(self.hass, candidate)" in source
    primary = source.split("async def _async_migrate_primary_tls", 1)[1].split(
        "async def _async_migrate_supplemental_tls", 1
    )[0]
    assert primary.index("await async_fetch_gateway_health") < primary.index(
        "async_update_entry"
    )
    assert "require_https: bool = True" in source
    assert "New and reconfigured REST sources must use verified HTTPS" in source
    assert 'DEFAULT_REST_ENDPOINT_URL: Final = "https://' in const_source
    assert "ssl=False" not in rest_source
    assert "verify=False" not in rest_source


def test_gateway_server_retains_tls_minimum_and_wire_schemas_are_unchanged() -> None:
    server = (GATEWAY / "server.py").read_text(encoding="utf-8")
    assert "context.minimum_version = ssl.TLSVersion.TLSv1_2" in server
    health = (GATEWAY / "server.py").read_text(encoding="utf-8")
    assert "health_schema_version" in health
    release = (ROOT / "docs" / "RELEASE-NOTES.md").read_text(encoding="utf-8")
    # These release-note strings are updated to 1.37.0 later in release preparation.
    assert "REST portfolio schema 1" in release
    assert "Gateway health schema 6" in release
    assert "payload schema 8" in release.lower()


def test_supervisor_tls_module_is_synced_to_all_official_apps() -> None:
    master = (GATEWAY / "supervisor_tls.py").read_bytes()
    sync = (ROOT / "tools" / "sync_gateway_app_sources.py").read_text(encoding="utf-8")
    assert '"supervisor_tls.py"' in sync
    for slug in APP_SLUGS:
        assert (
            APPS / slug / "src" / "portfolio_architect_gateway" / "supervisor_tls.py"
        ).read_bytes() == master
