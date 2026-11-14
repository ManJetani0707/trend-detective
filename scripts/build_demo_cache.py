"""Build the instant-demo cache. Run ONCE on your own computer with your Earthdata token.

    export EARTHDATA_TOKEN="<your new token>"      # Windows PowerShell: $env:EARTHDATA_TOKEN="..."
    python scripts/build_demo_cache.py             # all demos
    python scripts/build_demo_cache.py demo_gujarat_temp   # just one

Then commit data/demo_cache/*.nc to the repo so the Hugging Face Space never needs a login for demos.
Only the clipped boxes are saved (small files). The token is read from the environment and never written.

Original code written for NASA Space Apps 2026.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DEMOS, VARIABLES  # noqa: E402
from src.data import DataUnavailable, demo_path, fetch_earthaccess  # noqa: E402


def main(ids):
    ids = ids or list(DEMOS)
    for demo_id in ids:
        d = DEMOS[demo_id]
        var = VARIABLES[d["var"]]
        if not d.get("confirmed"):
            print(f"[note] {demo_id}: region/years are SUGGESTED, not confirmed. Edit src/config.py if needed.")
        print(f"Building {demo_id}: {var.label}, {d['years'][0]}-{d['years'][1]} ...")
        try:
            cube = fetch_earthaccess(var, d["bbox"], *d["years"],
                                     progress=lambda f, m: print(f"  {f:5.0%} {m}", end="\r"))
        except DataUnavailable as exc:
            print(f"\n  FAILED: {exc}")
            continue
        cube.attrs["demo_id"] = demo_id
        cube.to_netcdf(demo_path(demo_id))
        print(f"\n  saved {demo_path(demo_id)} ({demo_path(demo_id).stat().st_size/1e6:.2f} MB)")


if __name__ == "__main__":
    main(sys.argv[1:])
