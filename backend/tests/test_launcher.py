import subprocess
import sys
from pathlib import Path


def test_backend_launcher_exposes_options():
    backend = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(backend / 'main.py'), '--help'], cwd=backend, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert '--env' in result.stdout
    assert '--port' in result.stdout
