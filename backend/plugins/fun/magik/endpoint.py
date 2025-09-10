from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from .service import MagikService

router = APIRouter()


def get_magik_service() -> MagikService:
    return MagikService()


@router.post("/magik", summary="Apply magik distortion effect")
async def apply_magik(
    service: Annotated[MagikService, Depends(get_magik_service)],
    file: UploadFile = File(...),
    scale: int = Form(default=2, ge=1, le=10),
):
    image_bytes = BytesIO(await file.read())
    result_bytes, mime_type = service.do_magik(image_bytes, scale)
    return StreamingResponse(result_bytes, media_type=mime_type)


@router.post("/pixel", summary="Pixelate an image or GIF")
async def apply_pixel(
    service: Annotated[MagikService, Depends(get_magik_service)],
    file: UploadFile = File(...),
    pixels: int = Form(default=9, ge=2, le=50),
):
    image_bytes = BytesIO(await file.read())
    result_bytes, mime_type = service.do_pixelate(image_bytes, pixels)
    return StreamingResponse(result_bytes, media_type=mime_type)


@router.post("/mirror/{effect}", summary="Apply a mirroring effect")
async def apply_mirror(
    effect: str,
    service: Annotated[MagikService, Depends(get_magik_service)],
    file: UploadFile = File(...),
):
    if effect not in ["waaw", "haah", "woow", "hooh"]:
        return {"error": "Invalid effect type"}, 400
    image_bytes = BytesIO(await file.read())
    result_bytes, mime_type = service.do_mirror(image_bytes, effect)
    return StreamingResponse(result_bytes, media_type=mime_type)


@router.post("/transform/{transform_type}", summary="Apply a simple transformation")
async def apply_transform(
    transform_type: str,
    service: Annotated[MagikService, Depends(get_magik_service)],
    file: UploadFile = File(...),
):
    if transform_type not in ["flip", "flop", "invert"]:
        return {"error": "Invalid transform type"}, 400
    image_bytes = BytesIO(await file.read())
    result_bytes, mime_type = service.do_transform(image_bytes, transform_type)
    return StreamingResponse(result_bytes, media_type=mime_type)


@router.post("/rotate", summary="Rotate an image")
async def apply_rotate(
    service: Annotated[MagikService, Depends(get_magik_service)],
    file: UploadFile = File(...),
    degrees: int = Form(default=90, ge=-360, le=360),
):
    image_bytes = BytesIO(await file.read())
    result_bytes, mime_type = service.do_rotate(image_bytes, degrees)
    return StreamingResponse(result_bytes, media_type=mime_type)
