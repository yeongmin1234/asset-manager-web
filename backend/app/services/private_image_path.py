"""Resolve DB-owned image paths without allowing another uploads subtree."""

from pathlib import Path

from app.core.config import settings


def resolve_private_image_path(relative_path: str, subdir: str) -> Path:
    root = (Path(settings.upload_dir).resolve() / subdir).resolve()
    relative = Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts or "\\" in relative_path:
        raise ValueError("Invalid image path")
    target = (Path(settings.upload_dir).resolve() / relative).resolve()
    if root not in target.parents or not target.is_file():
        raise ValueError("Image file unavailable")
    return target
