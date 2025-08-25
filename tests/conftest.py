# Ensure the repo root is importable (so `import scripts.phase1.api` works under pytest).
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
