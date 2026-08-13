#!/usr/bin/env python3
"""Synchronize audited Gateway Python sources into provider App build contexts."""
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
MASTER=ROOT/"gateway"/"src"/"portfolio_architect_gateway"
COMDIRECT=ROOT/"home_assistant_app"/"portfolio_architect_gateway"/"src"/"portfolio_architect_gateway"
SHELLS=[
 ROOT/"home_assistant_app"/"portfolio_architect_gateway_dkb"/"src"/"portfolio_architect_gateway",
 ROOT/"home_assistant_app"/"portfolio_architect_gateway_trade_republic"/"src"/"portfolio_architect_gateway",
]
SHELL_FILES={"__init__.py","errors.py","models.py","provider.py","runtime_config.py","server.py","store.py","pending_app.py"}

def main():
    COMDIRECT.mkdir(parents=True,exist_ok=True)
    for p in MASTER.glob("*.py"):
        shutil.copy2(p,COMDIRECT/p.name)
    for target in SHELLS:
        target.mkdir(parents=True,exist_ok=True)
        for p in target.glob("*.py"):
            if p.name not in SHELL_FILES: p.unlink()
        for name in sorted(SHELL_FILES): shutil.copy2(MASTER/name,target/name)

if __name__=="__main__": main()
