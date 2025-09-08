import os
import yaml
import re
from pathlib import Path

def load_config(app) -> dict:
    # read stage from cdk context or env var; default 'dev'
    stage = app.node.try_get_context("stage") or os.getenv("STAGE", "dev")
    config_path = Path("configs") / f"{stage}_config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    
    with open(config_path, "r") as f:
        cfg_content = f.read()
    
    # Substitute environment variables
    cfg_content = substitute_env_vars(cfg_content)
    cfg = yaml.safe_load(cfg_content) or {}
    cfg["stage"] = stage
    return cfg

def substitute_env_vars(content: str) -> str:
    """
    Substitute environment variables in the format ${VAR_NAME} or ${VAR_NAME:default_value}
    """
    def replace_env_var(match):
        var_expr = match.group(1)
        if ':' in var_expr:
            var_name, default_value = var_expr.split(':', 1)
        else:
            var_name, default_value = var_expr, None
        
        env_value = os.getenv(var_name.strip())
        if env_value is not None:
            return env_value
        elif default_value is not None:
            return default_value.strip()
        else:
            raise ValueError(f"Environment variable '{var_name}' is required but not set")
    
    # Pattern to match ${VAR_NAME} or ${VAR_NAME:default}
    pattern = r'\$\{([^}]+)\}'
    return re.sub(pattern, replace_env_var, content)
