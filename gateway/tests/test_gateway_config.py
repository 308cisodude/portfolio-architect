from pathlib import Path

import pytest

from portfolio_architect_gateway.config import GatewayConfig, read_secret
from portfolio_architect_gateway.errors import ConfigurationError


def _write_config(tmp_path: Path, *, base_url: str = "https://api.comdirect.de") -> Path:
    secrets_dir = tmp_path / "secrets"
    data_dir = tmp_path / "data"
    secrets_dir.mkdir(parents=True)
    data_dir.mkdir()
    files = {
        "gateway": "g" * 64,
        "client_id": "client",
        "client_secret": "secret",
        "username": "user",
        "password": "password",
    }
    for name, value in files.items():
        path = secrets_dir / name
        path.write_text(value)
        path.chmod(0o600)
    config = tmp_path / "gateway.toml"
    config.write_text(
        f'''schema_version = 1
[server]
bind = "127.0.0.1"
port = 8787
api_token_file = "{secrets_dir / 'gateway'}"
snapshot_file = "{data_dir / 'portfolio.json'}"
[comdirect]
base_url = "{base_url}"
client_id_file = "{secrets_dir / 'client_id'}"
client_secret_file = "{secrets_dir / 'client_secret'}"
username_file = "{secrets_dir / 'username'}"
password_file = "{secrets_dir / 'password'}"
session_file = "{data_dir / 'session.json'}"
'''
    )
    return config


def test_config_accepts_only_exact_comdirect_origin(tmp_path: Path) -> None:
    config = GatewayConfig.load(_write_config(tmp_path))
    assert config.comdirect.base_url == "https://api.comdirect.de"
    with pytest.raises(ConfigurationError, match="exactly"):
        GatewayConfig.load(
            _write_config(tmp_path / "evil", base_url="https://api.comdirect.de.evil.example")
        )


def test_secret_permission_check_rejects_broad_native_file(tmp_path: Path) -> None:
    path = tmp_path / "secret"
    path.write_text("secret-value")
    path.chmod(0o644)
    with pytest.raises(ConfigurationError, match="unsafe"):
        read_secret(path, name="test")
