import datetime
from pathlib import Path

import nacl.encoding
import yaml
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from nacl.public import PrivateKey

SECRETS_DIR = Path("secrets")
CONFIG_FILE = Path("configs/banks.yaml")


def generate_cert(name: str, ca_cert=None, ca_key=None, is_ca=False):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, name),
        ]
    )

    if ca_cert and not is_ca:
        issuer = ca_cert.subject

    cert_builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.UTC))
        .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365))
    )

    if is_ca:
        cert_builder = cert_builder.add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
    else:
        cert_builder = cert_builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(name)]),
            critical=False,
        )

    signer_key = ca_key if ca_key else key
    cert = cert_builder.sign(signer_key, hashes.SHA256())

    return key, cert


def main():
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    Path("configs").mkdir(parents=True, exist_ok=True)

    # 1. Generate CA
    ca_key, ca_cert = generate_cert("mritra-ca", is_ca=True)
    with open(SECRETS_DIR / "ca.key", "wb") as f:
        f.write(
            ca_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    with open(SECRETS_DIR / "ca.crt", "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

    # 2. Generate Bank / Enclave Keys and Certs
    entities = ["enclave"] + [f"B{i}" for i in range(5)]
    banks_config = {"banks": {}}

    for entity in entities:
        # mTLS
        key, cert = generate_cert(entity, ca_cert, ca_key)

        with open(SECRETS_DIR / f"{entity}.key", "wb") as f:
            f.write(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
        with open(SECRETS_DIR / f"{entity}.crt", "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        # NaCl X25519
        nacl_sk = PrivateKey.generate()
        nacl_pk = nacl_sk.public_key

        with open(SECRETS_DIR / f"{entity}_nacl.sk", "wb") as f:
            f.write(nacl_sk.encode(encoder=nacl.encoding.Base64Encoder))

        # In a real environment, enclave PK is generated at boot.
        # But we also pre-generate one if the protocol says so for testing.
        if entity != "enclave":
            banks_config["banks"][entity] = nacl_pk.encode(
                encoder=nacl.encoding.Base64Encoder
            ).decode()

    with open(CONFIG_FILE, "w") as f:
        yaml.dump(banks_config, f)

    print(f"Generated CA and mTLS/NaCl keys for {len(entities)} entities in {SECRETS_DIR}")
    print(f"Wrote public keys to {CONFIG_FILE}")


if __name__ == "__main__":
    main()
