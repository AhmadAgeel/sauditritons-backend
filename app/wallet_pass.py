import base64
import hashlib
import io
import json
import struct
import zlib
import zipfile
from datetime import timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7

from app.config import settings


class WalletNotConfiguredError(RuntimeError):
    pass


def wallet_is_configured() -> bool:
    return all((
        settings.apple_wallet_pass_type_identifier,
        settings.apple_wallet_team_identifier,
        settings.apple_wallet_signing_cert_base64,
        settings.apple_wallet_signing_key_base64,
        settings.apple_wallet_wwdr_cert_base64,
    ))


def _decoded(value: str) -> bytes:
    return base64.b64decode("".join(value.split()))


def _certificate(value: str) -> x509.Certificate:
    raw = _decoded(value)
    return x509.load_pem_x509_certificate(raw) if raw.startswith(b"-----BEGIN") else x509.load_der_x509_certificate(raw)


def _solid_png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    row = b"\x00" + bytes(rgb) * width
    raw = row * height

    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def build_event_pass(*, ticket_code: str, holder_name: str, companion_count: int, event) -> bytes:
    if not wallet_is_configured():
        raise WalletNotConfiguredError

    starts_at = event.starts_at.astimezone(timezone.utc)
    pass_data = {
        "formatVersion": 1,
        "passTypeIdentifier": settings.apple_wallet_pass_type_identifier,
        "serialNumber": ticket_code,
        "teamIdentifier": settings.apple_wallet_team_identifier,
        "organizationName": settings.apple_wallet_organization_name,
        "description": f"Ticket for {event.title}",
        "logoText": "Saudi Students Association",
        "foregroundColor": "rgb(244, 240, 229)",
        "backgroundColor": "rgb(12, 52, 48)",
        "labelColor": "rgb(209, 168, 76)",
        "relevantDate": starts_at.isoformat().replace("+00:00", "Z"),
        "eventTicket": {
            "primaryFields": [{"key": "event", "label": "GATHERING", "value": event.title}],
            "secondaryFields": [
                {"key": "date", "label": "DATE", "value": starts_at.isoformat().replace("+00:00", "Z"), "dateStyle": "PKDateStyleMedium", "timeStyle": "PKDateStyleShort"},
                {"key": "location", "label": "LOCATION", "value": event.location or "Location to be announced"},
            ],
            "auxiliaryFields": [
                {"key": "holder", "label": "TICKET HOLDER", "value": holder_name},
                {"key": "party", "label": "PARTY", "value": 1 + companion_count},
            ],
            "backFields": [
                {"key": "ticket", "label": "Ticket code", "value": ticket_code},
                {"key": "checkin", "label": "Check-in", "value": "Present the QR code at the door. This ticket can be scanned once."},
            ],
        },
        "barcodes": [{"message": ticket_code, "format": "PKBarcodeFormatQR", "messageEncoding": "iso-8859-1", "altText": ticket_code}],
    }

    files = {
        "pass.json": json.dumps(pass_data, ensure_ascii=False, separators=(",", ":")).encode(),
        "icon.png": _solid_png(29, 29, (12, 52, 48)),
        "icon@2x.png": _solid_png(58, 58, (12, 52, 48)),
        "logo.png": _solid_png(160, 50, (12, 52, 48)),
        "logo@2x.png": _solid_png(320, 100, (12, 52, 48)),
    }
    manifest = {name: hashlib.sha1(content).hexdigest() for name, content in files.items()}
    manifest_bytes = json.dumps(manifest, separators=(",", ":")).encode()

    certificate = _certificate(settings.apple_wallet_signing_cert_base64)
    wwdr = _certificate(settings.apple_wallet_wwdr_cert_base64)
    password = settings.apple_wallet_signing_key_password.encode() or None
    key = serialization.load_pem_private_key(_decoded(settings.apple_wallet_signing_key_base64), password=password)
    signature = (
        pkcs7.PKCS7SignatureBuilder()
        .set_data(manifest_bytes)
        .add_signer(certificate, key, hashes.SHA256())
        .add_certificate(wwdr)
        .sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.Binary])
    )

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as package:
        for name, content in files.items():
            package.writestr(name, content)
        package.writestr("manifest.json", manifest_bytes)
        package.writestr("signature", signature)
    return output.getvalue()
