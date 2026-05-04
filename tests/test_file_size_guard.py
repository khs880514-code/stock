from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_entrypoint_files_stay_orchestrators():
    limits = {
        "app/web_ui.py": 1_100,
        "app/main.py": 750,
    }
    for relative_path, max_lines in limits.items():
        line_count = len((ROOT / relative_path).read_text(encoding="utf-8").splitlines())
        assert line_count <= max_lines, f"{relative_path} has {line_count} lines; split feature code first"


def test_web_feature_modules_stay_small():
    for path in (ROOT / "app" / "web").glob("*.py"):
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        assert line_count <= 350, f"{path.relative_to(ROOT)} has {line_count} lines; split panel/helper code"
