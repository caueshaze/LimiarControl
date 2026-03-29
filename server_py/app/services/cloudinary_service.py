import cloudinary
import cloudinary.uploader

from app.core.config import settings

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
UPLOAD_FOLDER = "limiarcontrol/entities"


def _configure() -> None:
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )


def upload_entity_image(file_bytes: bytes, content_type: str) -> str:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(f"Tipo de arquivo não suportado: {content_type}. Use JPEG, PNG, WebP ou GIF.")
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError("Arquivo muito grande. O tamanho máximo é 5 MB.")
    if not settings.cloudinary_cloud_name:
        raise RuntimeError("Cloudinary não configurado no servidor.")

    _configure()
    result = cloudinary.uploader.upload(
        file_bytes,
        folder=UPLOAD_FOLDER,
        resource_type="image",
        format="webp",
        transformation=[
            {"width": 512, "height": 512, "crop": "fill", "gravity": "auto"}
        ],
    )
    secure_url: str = result["secure_url"]
    return secure_url
