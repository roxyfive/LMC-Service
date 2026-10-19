import uuid
from io import BytesIO
from PIL import Image, ImageOps
from .config import UPLOADS, MAX_IMG, MAX_VID

IMG_EXT = {"jpg", "jpeg", "png", "webp"}
VID_EXT = {"mp4", "webm", "mov"}
SIZES = (480, 960, 1600)


def _is_video(head):
    return head[4:8] == b"ftyp" or head[:4] == b"\x1aE\xdf\xa3"


def save_image_obj(im, base):
    for w in SIZES:
        c = im.copy()
        c.thumbnail((w, w * 2))
        c.save(UPLOADS / f"{base}_{w}.webp", "WEBP", quality=82)


def save_upload(f):
    """Valida e salva un file. Ritorna (base, kind). Solleva ValueError se non valido."""
    name = (f.filename or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    data = f.read()
    if ext in IMG_EXT:
        if len(data) > MAX_IMG:
            raise ValueError("Immagine troppo pesante (max 12 MB)")
        try:
            Image.open(BytesIO(data)).verify()
            im = Image.open(BytesIO(data))
        except Exception:
            raise ValueError("File non è un'immagine valida")
        im = ImageOps.exif_transpose(im).convert("RGB")
        base = uuid.uuid4().hex
        save_image_obj(im, base)
        return base, "image"
    if ext in VID_EXT:
        if len(data) > MAX_VID:
            raise ValueError("Video troppo pesante (max 60 MB)")
        if not _is_video(data[:16]):
            raise ValueError("File non è un video valido")
        base = uuid.uuid4().hex
        (UPLOADS / f"{base}.{'webm' if ext == 'webm' else 'mp4'}").write_bytes(data)
        return base, "video"
    raise ValueError("Tipo di file non consentito (solo immagini jpg/png/webp e video mp4/webm)")


def delete_files(base):
    for p in UPLOADS.glob(f"{base}*"):
        p.unlink(missing_ok=True)
