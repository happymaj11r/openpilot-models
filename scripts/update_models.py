#!/usr/bin/env python3
"""
모델 폴더를 스캔해서 models.json을 자동 업데이트하는 스크립트

사용법:
  1. 새 폴더 생성: experimental_v1/
  2. ONNX 파일 추가:
     - experimental_v1/driving_policy.onnx
     - experimental_v1/driving_vision.onnx
  3. 스크립트 실행: python scripts/update_models.py
  4. 프롬프트에서 모델 이름/설명 입력
  5. 자동으로 models.json 업데이트 + 서명
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# 프로젝트 루트
ROOT_DIR = Path(__file__).parent.parent
MODELS_DIR = ROOT_DIR / "models"
MODELS_JSON = ROOT_DIR / "models.json"
README_FILE = ROOT_DIR / "README.md"
GITHUB_BASE_URL = "https://raw.githubusercontent.com/happymaj11r/openpilot-models/main/models"

# 필수 파일
REQUIRED_FILES = ["driving_policy.onnx", "driving_vision.onnx"]


def calculate_sha256(filepath: Path) -> str:
    """파일의 SHA256 해시 계산"""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def scan_model_folders() -> list[Path]:
    """models/ 폴더 내 모델 스캔 (ONNX 파일이 있는 폴더)"""
    model_folders = []

    # models 폴더가 없으면 생성
    MODELS_DIR.mkdir(exist_ok=True)

    for item in MODELS_DIR.iterdir():
        if item.is_dir():
            # 필수 파일 체크
            has_all_files = all((item / f).exists() for f in REQUIRED_FILES)
            if has_all_files:
                model_folders.append(item)

    return model_folders


def get_model_info(folder: Path, existing_models: dict) -> dict:
    """모델 폴더에서 정보 추출"""
    model_id = folder.name

    # 기존 모델 정보가 있으면 재사용
    existing = existing_models.get(model_id, {})

    # 파일 정보 계산
    files = {}
    for filename in REQUIRED_FILES:
        filepath = folder / filename
        files[filename] = {
            "size": filepath.stat().st_size,
            "sha256": calculate_sha256(filepath)
        }

    # 기존 정보가 있고 파일 해시가 같으면 기존 정보 유지
    if existing and existing.get("files") == files:
        print(f"  [{model_id}] 변경 없음 (기존 정보 유지)")
        return existing

    # 새 모델이거나 파일이 변경됨
    if existing:
        print(f"  [{model_id}] 파일 변경 감지!")
        name = existing.get("name", model_id)
        minimum_selector_version = existing.get("minimum_selector_version", 1)
    else:
        print(f"  [{model_id}] 새 모델 발견!")
        name = input(f"    모델 이름 (기본: {model_id}): ").strip() or model_id
        minimum_selector_version = 1

    return {
        "id": model_id,
        "name": name,
        "base_url": f"{GITHUB_BASE_URL}/{model_id}",
        "files": files,
        "minimum_selector_version": minimum_selector_version
    }


def update_readme(models: list):
    """README.md의 Models 테이블 업데이트"""
    if not README_FILE.exists():
        return

    content = README_FILE.read_text(encoding="utf-8")

    # Models 테이블 생성
    table_lines = [
        "## Models",
        "",
        "| ID | Name | Size |",
        "|----|------|------|",
    ]
    for m in models:
        size_mb = sum(f["size"] for f in m["files"].values()) / (1024 * 1024)
        table_lines.append(f"| {m['id']} | {m['name']} | {size_mb:.1f}MB |")
    table_lines.append("")

    # ## Models 부터 다음 ## 섹션 전까지 교체
    pattern = r"## Models\n.*?(?=\n## )"
    replacement = "\n".join(table_lines)
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    README_FILE.write_text(new_content, encoding="utf-8")
    print("README.md 업데이트 완료!")


def update_models_json():
    """models.json 업데이트"""
    print("=" * 50)
    print("모델 폴더 스캔 중...")
    print("=" * 50)

    # 기존 models.json 로드
    if MODELS_JSON.exists():
        with open(MODELS_JSON, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = {
            "version": 1,
            "updated_at": "",
            "models": [],
            "key_id": "key_2024_01",
            "signature": ""
        }

    # 기존 모델을 dict로 변환 (id -> model)
    existing_models = {m["id"]: m for m in manifest.get("models", [])}

    # 폴더 스캔
    folders = scan_model_folders()

    if not folders:
        print("\n모델 폴더를 찾을 수 없습니다.")
        print("폴더 구조 예시:")
        print("  openpilot-models/")
        print("  └── models/")
        print("      └── wmiv2/")
        print("          ├── driving_policy.onnx")
        print("          └── driving_vision.onnx")
        return

    print(f"\n{len(folders)}개 모델 폴더 발견:\n")

    # 각 폴더에서 모델 정보 추출
    new_models = []
    for folder in sorted(folders):
        model_info = get_model_info(folder, existing_models)
        new_models.append(model_info)

    # manifest 업데이트
    manifest["models"] = new_models
    manifest["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 서명 제거 (sign_manifest.py에서 다시 서명)
    manifest["signature"] = "NEEDS_SIGNING"

    # 저장
    with open(MODELS_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print(f"models.json 업데이트 완료! ({len(new_models)}개 모델)")
    print("=" * 50)

    # 서명 실행
    print("\n서명 중...")
    import subprocess
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "sign_manifest.py"), "--sign", str(MODELS_JSON)],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("서명 완료!")
    else:
        print(f"서명 실패: {result.stderr}")

    # README.md 업데이트
    update_readme(new_models)

    # 결과 출력
    print("\n" + "=" * 50)
    print("등록된 모델 목록:")
    print("=" * 50)
    for m in new_models:
        size_mb = sum(f["size"] for f in m["files"].values()) / (1024 * 1024)
        print(f"  - {m['id']}: {m['name']} ({size_mb:.1f}MB, selector v{m['minimum_selector_version']}+)")


if __name__ == "__main__":
    update_models_json()
