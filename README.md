# openpilot-models

Custom driving models for openpilot (carrot fork).

## Usage (콤마 기기에서)

1. openpilot UI에서 "주행 모델" 선택
2. 원하는 모델 다운로드
3. 자동으로 컴파일 및 적용

## Models

| ID | Name | Size |
|----|------|------|
| dark-souls-2 | Dark Souls 2 | 57.4MB |
| WMIv2 | WMIv2 | 44.1MB |

## 모델 추가 방법

자세한 사용법은 [docs/USAGE.md](docs/USAGE.md) 참조.

```bash
# 1. models 폴더에 새 모델 폴더 생성
mkdir -p models/my-model

# 2. ONNX 파일 복사
cp /path/to/driving_policy.onnx models/my-model/
cp /path/to/driving_vision.onnx models/my-model/

# 3. 스크립트 실행 (자동으로 models.json 업데이트 + 서명)
uv run python scripts/update_models.py

# 4. 커밋 및 푸시
git add . && git commit -m "feat: my-model 추가" && git push
```

## Structure

```
openpilot-models/
├── models.json            # Model metadata + signature
├── docs/
│   └── USAGE.md           # 상세 사용 가이드
├── scripts/
│   ├── update_models.py   # 모델 자동 등록 스크립트
│   ├── sign_manifest.py   # 서명 스크립트
│   └── keys/
│       ├── private_key.pem  # 개인키 (git 제외)
│       └── public_key.pem   # 공개키
└── models/                # 모델 저장 폴더
    └── {model_id}/
        ├── driving_policy.onnx
        └── driving_vision.onnx
```

## Security

All models are verified using Ed25519 signatures before download.
