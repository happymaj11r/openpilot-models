#!/usr/bin/env python3
"""
models.json 서명 스크립트

사용법:
  # 키 생성 (최초 1회)
  python sign_manifest.py --generate-key

  # 서명
  python sign_manifest.py --sign ../models.json

  # 검증 (테스트용)
  python sign_manifest.py --verify ../models.json
"""

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
except ImportError:
    print("cryptography 패키지가 필요합니다: pip install cryptography")
    sys.exit(1)


KEY_DIR = Path(__file__).parent / "keys"
PRIVATE_KEY_FILE = KEY_DIR / "private_key.pem"
PUBLIC_KEY_FILE = KEY_DIR / "public_key.pem"


def canonical_json(obj):
    """RFC 8785 JCS 간소화 - 재귀적 키 정렬 + compact"""
    if isinstance(obj, dict):
        return '{' + ','.join(
            json.dumps(k, ensure_ascii=False) + ':' + canonical_json(v)
            for k, v in sorted(obj.items())
        ) + '}'
    elif isinstance(obj, list):
        return '[' + ','.join(canonical_json(v) for v in obj) + ']'
    else:
        return json.dumps(obj, ensure_ascii=False)


def generate_keypair():
    """Ed25519 키쌍 생성"""
    KEY_DIR.mkdir(exist_ok=True)

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # 개인키 저장
    with open(PRIVATE_KEY_FILE, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # 공개키 저장
    with open(PUBLIC_KEY_FILE, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

    # 공개키 Base64 (코드에 하드코딩용)
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    public_key_b64 = base64.b64encode(public_key_bytes).decode()

    print(f"키 생성 완료!")
    print(f"  개인키: {PRIVATE_KEY_FILE}")
    print(f"  공개키: {PUBLIC_KEY_FILE}")
    print()
    print("=== 코드에 넣을 공개키 (Base64) ===")
    print(f'"{public_key_b64}"')
    print()
    print("=== common/keys.h에 추가 ===")
    print(f'{{"key_2025_01", "{public_key_b64}"}},')


def sign_manifest(manifest_path: Path):
    """models.json 서명"""
    if not PRIVATE_KEY_FILE.exists():
        print(f"개인키가 없습니다. 먼저 --generate-key를 실행하세요.")
        sys.exit(1)

    # 개인키 로드
    with open(PRIVATE_KEY_FILE, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)

    # manifest 로드
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 서명 대상에서 key_id, signature 제거
    manifest_to_sign = {k: v for k, v in manifest.items() if k not in ("key_id", "signature")}

    # Canonical JSON 생성
    canonical = canonical_json(manifest_to_sign)
    print(f"Canonical JSON:\n{canonical}\n")

    # SHA256 해시 (디버깅용)
    sha256_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    print(f"SHA256: {sha256_hash}\n")

    # 서명
    signature = private_key.sign(canonical.encode("utf-8"))
    signature_b64 = base64.b64encode(signature).decode()

    # manifest에 서명 추가
    manifest["signature"] = signature_b64

    # 저장
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"서명 완료!")
    print(f"  파일: {manifest_path}")
    print(f"  서명: {signature_b64[:50]}...")


def verify_manifest(manifest_path: Path):
    """models.json 서명 검증"""
    if not PUBLIC_KEY_FILE.exists():
        print(f"공개키가 없습니다.")
        sys.exit(1)

    # 공개키 로드
    with open(PUBLIC_KEY_FILE, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())

    # manifest 로드
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    signature_b64 = manifest.pop("signature")
    manifest.pop("key_id", None)

    # Canonical JSON
    canonical = canonical_json(manifest)

    # 검증
    signature = base64.b64decode(signature_b64)
    try:
        public_key.verify(signature, canonical.encode("utf-8"))
        print("서명 검증 성공!")
    except Exception as e:
        print(f"서명 검증 실패: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="models.json 서명 도구")
    parser.add_argument("--generate-key", action="store_true", help="Ed25519 키쌍 생성")
    parser.add_argument("--sign", type=Path, help="manifest 파일 서명")
    parser.add_argument("--verify", type=Path, help="manifest 서명 검증")

    args = parser.parse_args()

    if args.generate_key:
        generate_keypair()
    elif args.sign:
        sign_manifest(args.sign)
    elif args.verify:
        verify_manifest(args.verify)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
