"""Command-line entry point for validation, bootstrap, and service operation."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

from . import __version__
from .app import serve_app
from .comdirect import ComdirectClient
from .config import GatewayConfig, validate_runtime_files
from .errors import GatewayError
from .server import serve
from .store import save_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="portfolio-architect-gateway",
        description="Dedicated read-only Comdirect gateway for Portfolio Architect",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("/config/gateway.toml"),
        help="absolute path to gateway.toml (default: /config/gateway.toml)",
    )
    parser.add_argument(
        "--log-level",
        choices=("ERROR", "WARNING", "INFO", "DEBUG"),
        default="INFO",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check-config", help="validate configuration and required files")
    commands.add_parser(
        "bootstrap",
        help="run interactive Comdirect PhotoTAN authentication and fetch one snapshot",
    )
    commands.add_parser(
        "refresh-once",
        help="refresh the portfolio once using the persisted secondary session",
    )
    commands.add_parser("serve", help="start the authenticated local gateway")
    commands.add_parser(
        "serve-app",
        help="start the Home Assistant App runtime and Ingress setup UI",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        if args.command == "serve-app":
            serve_app()
            return 0
        config = GatewayConfig.load(args.config)
        bootstrap = args.command == "bootstrap"
        validate_runtime_files(config, bootstrap=bootstrap)
        if args.command == "check-config":
            print("Configuration and runtime files are valid.")
            return 0

        client = ComdirectClient(config.comdirect)
        if args.command == "bootstrap":
            client.bootstrap()
            snapshot = client.fetch_snapshot()
            save_snapshot(config.server.snapshot_file, snapshot)
            print(
                "Bootstrap completed and one provider-neutral snapshot was stored."
            )
            return 0
        if args.command == "refresh-once":
            snapshot = client.fetch_snapshot()
            save_snapshot(config.server.snapshot_file, snapshot)
            print("Portfolio snapshot refreshed successfully.")
            return 0
        if args.command == "serve":
            serve(config, client)
            return 0
        parser.error("unsupported command")
    except GatewayError as err:
        logging.getLogger(__name__).error("%s", err)
        return 2
    except OSError as err:
        logging.getLogger(__name__).error("Local operating-system error: %s", err)
        return 3
    return 1
