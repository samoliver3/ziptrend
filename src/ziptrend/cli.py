import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path

APP_HINT = 'The dashboard requires optional dependencies. Install them with: pip install "ziptrend[app]"'


def main():
    """Launch the local dashboard; pass additional Streamlit flags through."""
    missing = [name for name in ("streamlit", "plotly") if find_spec(name) is None]
    if missing:
        raise SystemExit(f"Missing {', '.join(missing)}. {APP_HINT}")
    raise SystemExit(subprocess.call([sys.executable, "-m", "streamlit", "run",
                                     str(Path(__file__).with_name("app.py")),
                                     "--server.address=127.0.0.1", *sys.argv[1:]]))
