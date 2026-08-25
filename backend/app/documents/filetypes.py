"""Allowlist de tipos de archivo para la evidencia de MOD·DOC.

El ``content_type`` que declara el navegador es texto libre del cliente — no
se confía en él ni al guardar ni al servir. El tipo real se deriva de la
extensión (allowlist cerrada) y, donde el formato tiene firma binaria, se
verifica que los primeros bytes correspondan (magic bytes): un ``.pdf`` que
no empieza con ``%PDF`` se rechaza con 415.
"""

# ext -> (media type que se sirve, prefijos binarios válidos o None si el
# formato no tiene firma, como el texto plano)
ALLOWED_TYPES: dict[str, tuple[str, tuple[bytes, ...] | None]] = {
    "pdf": ("application/pdf", (b"%PDF",)),
    "png": ("image/png", (b"\x89PNG\r\n\x1a\n",)),
    "jpg": ("image/jpeg", (b"\xff\xd8\xff",)),
    "jpeg": ("image/jpeg", (b"\xff\xd8\xff",)),
    # Office moderno (OOXML) es un ZIP; el legado usa el contenedor OLE2.
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", (b"PK\x03\x04",)),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", (b"PK\x03\x04",)),
    "pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", (b"PK\x03\x04",)),
    "doc": ("application/msword", (b"\xd0\xcf\x11\xe0",)),
    "xls": ("application/vnd.ms-excel", (b"\xd0\xcf\x11\xe0",)),
    "ppt": ("application/vnd.ms-powerpoint", (b"\xd0\xcf\x11\xe0",)),
    "txt": ("text/plain", None),
    "csv": ("text/csv", None),
    "md": ("text/markdown", None),
}


class DisallowedFileType(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def validate_and_resolve_type(filename: str, head: bytes) -> str:
    """Valida extensión + firma binaria y devuelve el media type a usar."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    entry = ALLOWED_TYPES.get(ext)
    if entry is None:
        allowed = ", ".join(sorted(ALLOWED_TYPES))
        raise DisallowedFileType(
            f"Tipo de archivo no permitido ('.{ext or 'sin extensión'}'). Permitidos: {allowed}"
        )
    media_type, magics = entry
    if magics is not None and not any(head.startswith(magic) for magic in magics):
        raise DisallowedFileType(
            f"El contenido del archivo no corresponde a la extensión .{ext}"
        )
    return media_type
