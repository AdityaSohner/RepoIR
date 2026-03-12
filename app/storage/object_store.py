from pathlib import Path
import shutil

BASE_PATH = Path("data/objects")

def save_file(source, object_id: str, obj_type: str, original_filename: str = None) -> str:
    dest_dir = BASE_PATH / obj_type
    dest_dir.mkdir(parents=True, exist_ok=True)

    if original_filename:
        ext = Path(original_filename).suffix
    elif isinstance(source, (str, Path)):
        ext = Path(source).suffix
    else:
        ext = ""

    dest_path = dest_dir / f"{object_id}{ext}"

    if isinstance(source, (str, Path)):
        shutil.copy(source, dest_path)
    else:
        # Assume it is a stream or bytes-like object
        if hasattr(source, 'seek'):
            source.seek(0)
        with open(dest_path, "wb") as f:
            if hasattr(source, 'read'):
                f.write(source.read())
            else:
                f.write(source)
    
    return str(dest_path)
