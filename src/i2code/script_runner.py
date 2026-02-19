import os
import subprocess
from pathlib import Path


def run_script(script_name, args=()):
    script_path = Path(__file__).parent / "scripts" / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Bundled script not found: {script_name}")
    os.chmod(script_path, script_path.stat().st_mode | 0o111)
    return subprocess.run([str(script_path)] + list(args))
