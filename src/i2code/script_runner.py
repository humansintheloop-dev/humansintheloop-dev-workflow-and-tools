import stat
import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent / "scripts"


def run_script(script_name, args=()):
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_name}")

    current_mode = script_path.stat().st_mode
    if not current_mode & stat.S_IXUSR:
        script_path.chmod(current_mode | stat.S_IXUSR)

    return subprocess.run([str(script_path)] + list(args))
