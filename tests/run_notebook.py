"""Execute marimo notebooks headlessly; any cell error raises and exits non-zero.

    uv run python tests/run_notebook.py                                     # every notebook, in order
    uv run python tests/run_notebook.py notebooks/01_where_is_it_hot.py      # one
    uv run python tests/run_notebook.py "notebooks/0*.py"                   # a pattern (works in PowerShell too)
"""

import glob
import importlib.util
import sys
import time
from pathlib import Path

NOTEBOOKS = Path(__file__).resolve().parents[1] / "notebooks"


def run(path: str) -> None:
    spec = importlib.util.spec_from_file_location("nb", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    t0 = time.time()
    _, defs = mod.app.run()
    shown = Path(path).resolve()
    shown = shown.relative_to(NOTEBOOKS.parent) if shown.is_relative_to(NOTEBOOKS.parent) else shown
    print(f"ok  {shown.as_posix()}  ({len(defs)} definitions, {time.time() - t0:.1f}s)")


if __name__ == "__main__":
    # PowerShell and cmd pass patterns like notebooks/*.py through unexpanded, so expand them here
    paths = [p for arg in sys.argv[1:] for p in (sorted(glob.glob(arg)) or [arg])]
    for p in paths or sorted(str(p) for p in NOTEBOOKS.glob("*.py")):
        run(p)
