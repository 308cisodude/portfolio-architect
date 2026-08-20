#!/usr/bin/env python3
"""Synchronize audited Gateway Python sources into provider App build contexts."""
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
MASTER=ROOT/"gateway"/"src"/"portfolio_architect_gateway"
COMDIRECT=ROOT/"home_assistant_app"/"portfolio_architect_gateway"/"src"/"portfolio_architect_gateway"
DKB=ROOT/"home_assistant_app"/"portfolio_architect_gateway_dkb"/"src"/"portfolio_architect_gateway"
TRADE_REPUBLIC=ROOT/"home_assistant_app"/"portfolio_architect_gateway_trade_republic"/"src"/"portfolio_architect_gateway"
SHELL_FILES={"__init__.py","errors.py","human_input.py","models.py","provider.py","runtime_config.py","server.py","store.py","pending_app.py","supervisor_tls.py"}
DKB_PROVIDER_FILES={"dkb_app.py","dkb_fints.py"}
TR_PROVIDER_FILES={"trade_republic_app.py","trade_republic_statement.py"}


def _sync_shell(target: Path, *, provider_files: set[str]) -> None:
    target.mkdir(parents=True,exist_ok=True)
    allowed=SHELL_FILES | provider_files
    for p in target.glob("*.py"):
        if p.name not in allowed:
            p.unlink()
    for name in sorted(SHELL_FILES):
        shutil.copy2(MASTER/name,target/name)


def main():
    COMDIRECT.mkdir(parents=True,exist_ok=True)
    for p in MASTER.glob("*.py"):
        shutil.copy2(p,COMDIRECT/p.name)
    _sync_shell(DKB, provider_files=DKB_PROVIDER_FILES)
    _sync_shell(TRADE_REPUBLIC, provider_files=TR_PROVIDER_FILES)


if __name__=="__main__":
    main()
