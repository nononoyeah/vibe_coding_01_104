from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def resolve_data_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.is_absolute():
        path = BACKEND_DIR / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
