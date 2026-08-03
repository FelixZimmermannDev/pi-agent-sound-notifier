"""Portable Stockfish executable discovery shared by local adapters."""

import os
from pathlib import Path
import shutil


def resolve_engine_path(command_line_path: str | None) -> str:
    explicit_path = command_line_path or os.environ.get("STOCKFISH_PATH")
    if explicit_path:
        return explicit_path

    path_executable = shutil.which("stockfish")
    if path_executable:
        return path_executable

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        package_root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        candidates = sorted(
            package_root.glob("Stockfish.Stockfish_*/stockfish/stockfish*.exe")
        )
        if candidates:
            return str(candidates[-1])

    return "stockfish"
