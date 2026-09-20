import base64
from io import BytesIO
import unittest

from PIL import Image

from app.storage import EVENT_IMAGE_KEY_RE, InvalidImageError, decode_inline_image, prepare_event_image


class ImageStorageTests(unittest.TestCase):
    def test_prepares_high_quality_webp_with_bounded_dimensions(self):
        source = BytesIO()
        Image.new("RGB", (3200, 1800), (12, 52, 48)).save(source, format="PNG")

        output, width, height = prepare_event_image(source.getvalue())

        self.assertEqual((width, height), (2400, 1350))
        with Image.open(BytesIO(output)) as image:
            self.assertEqual(image.format, "WEBP")
            self.assertEqual(image.size, (2400, 1350))

    def test_decodes_supported_inline_image(self):
        raw = b"ssa-image"
        value = "data:image/png;base64," + base64.b64encode(raw).decode()
        self.assertEqual(decode_inline_image(value), raw)

    def test_rejects_invalid_data(self):
        with self.assertRaises(InvalidImageError):
            prepare_event_image(b"not-an-image")
        with self.assertRaises(InvalidImageError):
            decode_inline_image("data:text/plain;base64,SGVsbG8=")

    def test_media_proxy_only_accepts_generated_event_keys(self):
        self.assertIsNotNone(EVENT_IMAGE_KEY_RE.fullmatch("events/0123456789abcdef0123456789abcdef.webp"))
        self.assertIsNone(EVENT_IMAGE_KEY_RE.fullmatch("database/backup.dump.gz"))
        self.assertIsNone(EVENT_IMAGE_KEY_RE.fullmatch("events/../../secret.webp"))


if __name__ == "__main__":
    unittest.main()
