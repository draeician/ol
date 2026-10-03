"""Clipboard helpers for `ol --ocr`.

Narrowly scoped to reading an image from the system clipboard (returned as
in-memory PNG base64) and writing plain text back to the clipboard. No
temporary files are created.
"""

import base64
import io

from PIL import Image, ImageGrab


class ClipboardError(RuntimeError):
    """Raised when clipboard input or output cannot be accessed."""


_CLIPBOARD_READ_HINT = (
    "Failed to read an image from the clipboard. Copy an image (e.g. a "
    "screenshot) and try again. On Linux, install xclip (X11) or "
    "wl-clipboard (Wayland) for clipboard image support."
)


def get_clipboard_image_base64() -> str:
    """
    Read an image from the system clipboard and return it as base64 PNG.

    Returns:
        str: ASCII base64 encoding of the clipboard image's PNG bytes.

    Raises:
        ClipboardError: If the clipboard holds no image, holds a non-image
            result (e.g. a list of filenames), or the backend fails.
    """
    try:
        item = ImageGrab.grabclipboard()
    except Exception as exc:  # pragma: no cover - platform dependent
        raise ClipboardError(_CLIPBOARD_READ_HINT) from exc

    if item is None:
        raise ClipboardError(_CLIPBOARD_READ_HINT)

    if not isinstance(item, Image.Image):
        raise ClipboardError(_CLIPBOARD_READ_HINT)

    image = item
    try:
        buffer = io.BytesIO()
        try:
            image.save(buffer, format="PNG")
            data = buffer.getvalue()
        finally:
            buffer.close()
    except Exception as exc:  # pragma: no cover - platform dependent
        raise ClipboardError(
            f"Failed to encode clipboard image: {exc}"
        ) from exc
    finally:
        _release_image(image)

    return base64.b64encode(data).decode("ascii")


def _release_image(image: Image.Image) -> None:
    """Release image resources where the backend supports it."""
    close = getattr(image, "close", None)
    if callable(close):
        try:
            close()
        except Exception:  # pragma: no cover - backend specific
            pass


def set_clipboard_text(text: str) -> None:
    """
    Replace the system clipboard contents with the given plain text.

    Args:
        text: The text to copy to the clipboard.

    Raises:
        ClipboardError: If the clipboard cannot be written.
    """
    try:
        import pyperclip

        pyperclip.copy(text)
    except Exception as exc:  # pragma: no cover - platform dependent
        raise ClipboardError(
            f"Failed to write text to the clipboard: {exc}"
        ) from exc
