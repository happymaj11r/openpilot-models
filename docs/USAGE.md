# openpilot-models 사용 가이드

## 개요

이 저장소는 openpilot용 커스텀 주행 모델을 관리합니다.
콤마 기기에서 모델을 선택하면 이 저장소에서 다운로드됩니다.

## 저장소 구조

```
openpilot-models/
├── models.json                 # 모델 메타데이터 + Ed25519 서명
├── docs/
│   └── USAGE.md                # 이 문서
├── scripts/
│   ├── update_models.py        # 모델 자동 등록 스크립트
│   ├── sign_manifest.py        # 서명 스크립트
│   └── keys/
│       ├── private_key.pem     # 개인키 (git 제외, 절대 공유 금지!)
│       └── public_key.pem      # 공개키
└── models/                     # 모델 저장 폴더
    └── {model-id}/
        ├── driving_policy.onnx
        └── driving_vision.onnx
```

---

## 새 모델 추가하기

### 1단계: 모델 폴더 생성

```bash
# models/ 폴더 안에 새 폴더 생성
mkdir -p models/my-new-model
```

**폴더명 규칙:**
- 영문, 숫자, 하이픈(`-`), 언더스코어(`_`)만 사용
- 공백 사용 금지 (URL 문제 발생)
- 예시: `wmi-v2`, `experimental_v1`, `dark-souls-2`

### 2단계: ONNX 파일 복사

```bash
# 필수 파일 2개
cp /path/to/driving_policy.onnx models/my-new-model/
cp /path/to/driving_vision.onnx models/my-new-model/
```

**필수 파일:**
| 파일명 | 설명 | 대략적 크기 |
|--------|------|-------------|
| `driving_policy.onnx` | 정책 모델 | ~14MB |
| `driving_vision.onnx` | 비전 모델 | ~46MB |

### 3단계: 스크립트 실행

```bash
# 자동으로 models.json 업데이트 + 서명
uv run python scripts/update_models.py
```

스크립트가 물어보는 것:
- **모델 이름**: UI에 표시될 이름 (한글 가능, 예: "WMI v2 모델")
- 엔터만 치면 폴더명이 이름으로 사용됨

### 4단계: 커밋 및 푸시

```bash
git add .
git commit -m "feat: my-new-model 모델 추가"
git push
```

---

## 스크립트 상세 설명

### update_models.py

모델 폴더를 스캔해서 `models.json`을 자동으로 업데이트합니다.

```bash
# 실행
uv run python scripts/update_models.py
```

**동작:**
1. `models/` 폴더 내 모든 하위 폴더 스캔
2. 각 폴더에 필수 ONNX 파일이 있는지 확인
3. 새 모델이면 이름 입력 요청
4. 기존 모델의 파일이 변경되면 해시 업데이트
5. `models.json` 저장 후 자동 서명

**출력 예시:**
```
==================================================
모델 폴더 스캔 중...
==================================================

2개 모델 폴더 발견:

  [dark-souls-2] 변경 없음 (기존 정보 유지)
  [wmi-v3] 새 모델 발견!
    모델 이름 (기본: wmi-v3): WMI v3

==================================================
models.json 업데이트 완료! (2개 모델)
==================================================

서명 중...
서명 완료!

==================================================
등록된 모델 목록:
==================================================
  - dark-souls-2: Dark Souls 2 (57.4MB, selector v1+)
  - wmi-v3: WMI v3 (58.1MB, selector v1+)
```

---

### sign_manifest.py

Ed25519 키 생성 및 `models.json` 서명을 담당합니다.

#### 키 생성 (최초 1회만)

```bash
uv run python scripts/sign_manifest.py --generate-key
```

**출력:**
- `scripts/keys/private_key.pem` - 개인키 (절대 공유 금지!)
- `scripts/keys/public_key.pem` - 공개키
- 콘솔에 `common/keys.h`에 넣을 공개키 Base64 출력

#### 수동 서명

```bash
uv run python scripts/sign_manifest.py --sign models.json
```

> 보통은 `update_models.py`가 자동으로 서명하므로 수동 실행할 일은 거의 없음

#### 서명 검증 (테스트용)

```bash
uv run python scripts/sign_manifest.py --verify models.json
```

---

## models.json 구조

```json
{
  "version": 1,
  "updated_at": "2025-12-19T04:38:39Z",
  "models": [
    {
      "id": "dark-souls-2",
      "name": "Dark Souls 2",
      "base_url": "https://raw.githubusercontent.com/happymaj11r/openpilot-models/main/models/dark-souls-2",
      "files": {
        "driving_policy.onnx": {
          "size": 13926324,
          "sha256": "f8fe9a71b0fd428a..."
        },
        "driving_vision.onnx": {
          "size": 46271942,
          "sha256": "1dc66bc06f250b57..."
        }
      },
      "minimum_selector_version": 1
    }
  ],
  "key_id": "key_2025_01",
  "signature": "9AtuADaNjUNbI5VK..."
}
```

**필드 설명:**

| 필드 | 설명 |
|------|------|
| `id` | 모델 고유 ID (폴더명과 동일) |
| `name` | UI에 표시될 이름 |
| `base_url` | 파일 다운로드 기본 URL |
| `files` | 파일별 크기(bytes)와 SHA256 해시 |
| `minimum_selector_version` | 최소 모델 셀렉터 버전 |
| `key_id` | 서명에 사용된 키 ID |
| `signature` | Ed25519 서명 (Base64) |

---

## 보안

### 개인키 관리

- `scripts/keys/private_key.pem`은 **절대 공유하면 안 됨**
- `.gitignore`에 이미 등록되어 있음
- 개인키가 유출되면 새 키를 생성하고 openpilot 코드의 공개키도 업데이트해야 함

### 서명 검증 흐름

```
1. 콤마 기기가 models.json 다운로드
2. key_id로 공개키 선택 (openpilot 코드에 하드코딩)
3. Ed25519 서명 검증
4. 검증 실패 시 다운로드 차단
5. 검증 성공 시 ONNX 파일 다운로드
6. 각 파일의 SHA256 해시 검증
```

---

## 문제 해결

### "모델 폴더를 찾을 수 없습니다"

- `models/` 폴더가 있는지 확인
- 폴더 안에 `driving_policy.onnx`와 `driving_vision.onnx`가 둘 다 있는지 확인

### "서명 실패"

- `scripts/keys/private_key.pem` 파일이 있는지 확인
- 없으면 `--generate-key`로 새로 생성 (단, 기존 서명과 호환 안 됨)

### 폴더명에 공백이 있으면?

공백이 있는 폴더명은 URL 문제를 일으킵니다:
```
# 나쁜 예
models/Dark Souls 2/

# 좋은 예
models/dark-souls-2/
```

---

## 체크리스트

새 모델 추가 시:

- [ ] 폴더명에 공백 없음
- [ ] `driving_policy.onnx` 있음
- [ ] `driving_vision.onnx` 있음
- [ ] `update_models.py` 실행함
- [ ] 모델 이름 입력함 (또는 기본값 사용)
- [ ] git commit & push 함
