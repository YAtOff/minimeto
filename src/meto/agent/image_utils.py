import base64
import mimetypes
import re
from pathlib import Path


def is_image(path: str) -> bool:
    """Check if a file path points to an image based on its extension."""
    mime, _ = mimetypes.guess_type(path)
    return bool(mime and mime.startswith("image/"))


def encode_image(path: str) -> tuple[str, str]:
    """Read an image file and return its MIME type and Base64 encoded content.

    Returns:
        tuple[str, str]: (mime_type, base64_data)
    """
    p = Path(path)
    mime, _ = mimetypes.guess_type(str(p))
    if not mime:
        mime = "image/png"  # Fallback

    data = p.read_bytes()
    encoded = base64.b64encode(data).decode("utf-8")
    return mime, encoded


def detect_images_in_prompt(prompt: str) -> list[str]:
    """Scan the prompt for potential image file paths that exist on disk.

    Returns:
        list[str]: List of absolute paths to detected image files.
    """
    # Match potential paths with image extensions
    # Matches alphanumeric, dots, slashes, and hyphens followed by image extension
    pattern = r"[\w\/\.\-]+\.(?:png|jpg|jpeg|webp|gif)"
    matches = re.findall(pattern, prompt)

    valid_images = []
    for match in matches:
        try:
            p = Path(match).expanduser().resolve()
            if p.exists() and p.is_file() and is_image(str(p)):
                valid_images.append(str(p))
        except (OSError, RuntimeError):
            # Skip invalid paths or permission issues during scanning
            continue

    return valid_images
