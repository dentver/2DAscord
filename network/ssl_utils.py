import ssl
import asyncio
import threading
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_rsa_key(bits: int = 2048):
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=bits,
    )


def generate_self_signed_cert(key) -> tuple[bytes, bytes]:
    import datetime

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "2DAscord"),
    ])

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return cert_pem, key_pem


# ── SSL context creation ─────────────────────────────────

def create_server_ssl_context(cert_pem: bytes, key_pem: bytes) -> ssl.SSLContext:
    from .logger import step_start, step_ok, step_fail
    step_start("SSL_CTX", "creating SSL context")

    cert_text = cert_pem.decode('ascii')
    key_text = key_pem.decode('ascii')

    cert_path = Path("_2da_cert.pem")
    key_path = Path("_2da_key.pem")
    try:
        cert_path.write_text(cert_text, encoding='ascii')
        key_path.write_text(key_text, encoding='ascii')

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(str(cert_path), str(key_path))
        step_ok("SSL_CTX", "cert chain loaded")
        return ctx
    except Exception as e:
        step_fail("SSL_CTX", f"error: {e}")
        raise
    finally:
        for p in (cert_path, key_path):
            try:
                p.unlink()
            except Exception:
                pass


def create_client_ssl_context() -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def generate_session_certs() -> tuple[ssl.SSLContext, ssl.SSLContext]:
    key = generate_rsa_key(2048)
    cert_pem, key_pem = generate_self_signed_cert(key)
    server_ctx = create_server_ssl_context(cert_pem, key_pem)
    client_ctx = create_client_ssl_context()
    return server_ctx, client_ctx


# ── Background RSA key generation ──────────────────────

_rsa_key = None
_rsa_event = threading.Event()


def _generate_key_in_thread():
    global _rsa_key
    from .logger import step_start, step_ok, step_fail
    step_start("RSA_GEN", "generating 2048-bit key in thread")
    try:
        _rsa_key = generate_rsa_key(2048)
        _rsa_event.set()
        step_ok("RSA_GEN", "key ready")
    except Exception as e:
        step_fail("RSA_GEN", str(e))


def init_rsa_key():
    if _rsa_event.is_set():
        return
    from .logger import step_ok
    t = threading.Thread(target=_generate_key_in_thread, daemon=True)
    t.start()
    step_ok("RSA_INIT", "background thread started")


async def get_rsa_key():
    from .logger import step_start, step_ok, step_fail
    if _rsa_key is not None:
        step_ok("RSA_GET", "key already ready")
        return _rsa_key
    step_start("RSA_GET", "waiting for key...")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _rsa_event.wait)
    if _rsa_key is None:
        step_fail("RSA_GET", "key generation failed")
        raise RuntimeError("RSA key generation failed")
    step_ok("RSA_GET", "key obtained")
    return _rsa_key
