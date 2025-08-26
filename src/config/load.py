import os
import yaml
from pathlib import Path

def load_config(app) -> dict:
    # read stage from cdk context or env var; default 'dev'
    stage = app.node.try_get_context("stage") or os.getenv("STAGE", "dev")
    config_path = Path("configs") / f"{stage}_config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f) or {}
    cfg["stage"] = stage
    return cfg
