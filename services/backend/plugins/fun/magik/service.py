from io import BytesIO

import magic
import wand.color
import wand.drawing
import wand.image
from PIL import Image, ImageOps, ImageSequence
from structlog import get_logger
from utils.exceptions import BadRequestError

log = get_logger(__name__)


class MagikService:
    def __init__(self):
        self.supported_mimes = [
            "image/png",
            "image/jpeg",
            "image/pjpeg",
            "image/gif",
        ]
        log.info("MagikService initialized")

    def _validate_mime(self, media_bytes: BytesIO):
        media_bytes.seek(0)
        mime_type = magic.from_buffer(media_bytes.read(2048), mime=True)
        media_bytes.seek(0)
        if mime_type not in self.supported_mimes:
            raise BadRequestError(f"Unsupported image format: {mime_type}")
        return mime_type == "image/gif"

    def _process_gif_frames(self, image: wand.image.Image, process_func, *args):
        frames = []
        for frame in image.sequence:
            with frame.clone() as img:
                processed_frame = process_func(img, *args)
                frames.append(processed_frame.clone())
        return frames

    def _save_gif(self, frames) -> BytesIO:
        output = BytesIO()
        with wand.image.Image() as gif:
            gif.sequence.extend(frames)
            for frame in gif.sequence:
                frame.dispose = "background"
            gif.format = "gif"
            gif.save(file=output)
        output.seek(0)
        return output

    def _save_image(self, image: wand.image.Image) -> BytesIO:
        output = BytesIO()
        image.format = "png"
        image.save(file=output)
        output.seek(0)
        return output

    def do_magik(self, img_bytes: BytesIO, scale: int) -> tuple[BytesIO, str]:
        is_gif = self._validate_mime(img_bytes)
        with wand.image.Image(blob=img_bytes.getvalue()) as img:
            if is_gif:
                frames = self._process_gif_frames(img, self._apply_magik_effect, scale)
                result_bytes = self._save_gif(frames)
                return result_bytes, "image/gif"
            else:
                processed_img = self._apply_magik_effect(img.clone(), scale)
                result_bytes = self._save_image(processed_img)
                return result_bytes, "image/png"

    def _apply_magik_effect(self, image: wand.image.Image, scale: int):
        image.transform(resize="800x800>")
        image.liquid_rescale(
            width=int(image.width * 0.5),
            height=int(image.height * 0.5),
            delta_x=int(0.5 * scale) if scale else 1,
            rigidity=0,
        )
        image.liquid_rescale(
            width=int(image.width * 1.5),
            height=int(image.height * 1.5),
            delta_x=scale if scale else 2,
            rigidity=0,
        )
        return image

    def do_pixelate(self, img_bytes: BytesIO, pixels: int) -> tuple[BytesIO, str]:
        is_gif = self._validate_mime(img_bytes)
        img = Image.open(img_bytes)

        def _pixelate_frame(frame: Image.Image, p: int):
            frame = frame.convert("RGBA")
            small = frame.resize(
                (frame.size[0] // p, frame.size[1] // p), Image.NEAREST
            )
            return small.resize(frame.size, Image.NEAREST)

        if is_gif:
            frames = [
                _pixelate_frame(frame.copy(), pixels)
                for frame in ImageSequence.Iterator(img)
            ]
            output = BytesIO()
            frames[0].save(
                output, format="GIF", save_all=True, append_images=frames[1:], loop=0
            )
            output.seek(0)
            return output, "image/gif"
        else:
            pixelated_img = _pixelate_frame(img, pixels)
            output = BytesIO()
            pixelated_img.save(output, "PNG")
            output.seek(0)
            return output, "image/png"

    def _mirror_side(
        self, img: wand.image.Image, side: str, axis: str
    ) -> wand.image.Image:
        half_dim = int(img.width / 2) if side == "vertical" else int(img.height / 2)

        crop_params = {
            ("vertical", "east"): (img.width - half_dim, 0, img.width, img.height),
            ("vertical", "west"): (0, 0, half_dim, img.height),
            ("horizontal", "north"): (0, 0, img.width, half_dim),
            ("horizontal", "south"): (0, img.height - half_dim, img.width, img.height),
        }

        left, top, right, bottom = crop_params[(side, axis)]

        with img[left:right, top:bottom] as half:
            opposite = half.clone()
            if side == "vertical":
                opposite.flop()
                if axis == "east":
                    img.composite(opposite, left=0, top=0)
                else:
                    img.composite(opposite, left=half_dim, top=0)
            else:
                opposite.flip()
                if axis == "north":
                    img.composite(opposite, left=0, top=half_dim)
                else:
                    img.composite(opposite, left=0, top=0)
        return img

    def do_mirror(self, img_bytes: BytesIO, effect: str) -> tuple[BytesIO, str]:
        is_gif = self._validate_mime(img_bytes)

        effects_map = {
            "waaw": ("vertical", "east"),
            "haah": ("vertical", "west"),
            "woow": ("horizontal", "north"),
            "hooh": ("horizontal", "south"),
        }
        side, axis = effects_map[effect]

        with wand.image.Image(blob=img_bytes.getvalue()) as img:
            if is_gif:
                frames = self._process_gif_frames(img, self._mirror_side, side, axis)
                result_bytes = self._save_gif(frames)
                return result_bytes, "image/gif"
            else:
                processed_img = self._mirror_side(img.clone(), side, axis)
                result_bytes = self._save_image(processed_img)
                return result_bytes, "image/png"

    def do_transform(
        self, img_bytes: BytesIO, transform_type: str
    ) -> tuple[BytesIO, str]:
        self._validate_mime(img_bytes)
        img = Image.open(img_bytes)

        if transform_type == "flip":
            transformed = ImageOps.flip(img)
        elif transform_type == "flop":
            transformed = ImageOps.mirror(img)
        elif transform_type == "invert":
            transformed = ImageOps.invert(img.convert("RGB"))
        else:
            raise BadRequestError("Invalid transform type")

        output = BytesIO()
        transformed.save(output, "PNG")
        output.seek(0)
        return output, "image/png"

    def do_rotate(self, img_bytes: BytesIO, degrees: int) -> tuple[BytesIO, str]:
        self._validate_mime(img_bytes)
        img = Image.open(img_bytes).convert("RGBA")
        rotated = img.rotate(degrees, expand=True)

        output = BytesIO()
        rotated.save(output, "PNG")
        output.seek(0)
        return output, "image/png"
