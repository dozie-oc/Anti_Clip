"""File service — helpers for moving and managing uploaded files."""
import os
import shutil
from app.core.storage import get_project_upload_dir


def move_temp_file_to_project(temp_path: str, project_id: str, filename: str) -> str:
    """Move a file from temp storage to its project folder."""
    dest_dir = get_project_upload_dir(project_id)
    dest_path = os.path.join(dest_dir, filename)
    shutil.move(temp_path, dest_path)
    return dest_path


def delete_project_files(project_id: str, upload_dir: str, clips_dir: str) -> None:
    """Remove all files associated with a project."""
    for base_dir in [upload_dir, clips_dir]:
        project_dir = os.path.join(base_dir, project_id)
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)


def format_file_size(size_bytes: int) -> str:
    """Human-readable file size string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
