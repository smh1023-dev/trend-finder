# 글로벌 트렌드 파인더 — 일일 자동 상품 발굴

매일 아침 7시(한국시간)에 자동으로 해외 트렌드 데이터를 수집해
한국 진입 후보 상품 5개를 발굴하는 시스템입니다.

## 핵심 컨셉

**"해외 수요는 증가 중이지만 한국 공급·콘텐츠 경쟁은 약한 틈새 상품"** 매일 발굴.

단순 인기 상품이 아니라 6단계 검증 통과 후보만 선정:
1. ✅ 해외 검색량 상승
2. ✅ 한국 검색량 낮음 (갭 존재)
3. ✅ 콘텐츠화 가능 (시각적·감성적)
4. ✅ 저위험 (소형·경량·2~5만원대 추정)
5. ✅ 행동경제학·치알디니 심리 자극 가능
6. ✅ 충동/반복 구매 영역

## 결과물

매일 자동 생성:
- `index.html` — 5개 후보 한눈에 보는 메인
- `1번_상품명_트렌드리포트.html` ~ `5번_상품명_트렌드리포트.html` — 각 상품 상세 분석

URL: `https://[당신의-username].github.io/[저장소-이름]/`

## 각 상품별 분석 항목

1. **왜 뜨는가** — 해외 트렌드 근거 / 검색량 증가 이유 / 소비자 반응 이유
2. **왜 한국에 갭이 있는가** — 공급 부족 / 브랜딩 부족 / 콘텐츠 부족
3. **예상 타깃** — 연령/성별 / 구매 상황 / 핵심 감정 포인트
4. **심리 분석** — 치알디니 + 카너먼 요소 + 저장/공유 트리거
5. **릴스 후킹 6종** — 첫1초/스크롤멈춤/저장유도/댓글유도/구매충동/CTA
6. **수익화 추정** — 예상 판매가/원가/마진/한국 성공 가능성 (10점)

## 데이터 소스 (미국 우선)

- **Google Trends** (US + KR 비교) — 검색량 momentum
- **Amazon Movers & Shakers** — 24시간 급상승 상품 (7개 카테고리)
- **Etsy 인기 상품** — 감성 소비 카테고리

⚠️ **솔직히 짚을 한계**: Amazon과 Etsy는 봇 차단이 있어서 가끔 데이터 수집 실패합니다. 그럴 때도 Google Trends로 보고서는 생성됩니다.

## 자체 포함 구조 (data 폴더 없음)

종목 데이터(시드 키워드 + 카테고리)가 모두 `seed_keywords.py`에 내장.
파일 위치 어디든 상관없이 작동합니다.

## 파일 구조

```
trend-finder/
├── .github/workflows/daily_trends.yml    # 매일 KST 7시 자동 실행
├── templates/
│   ├── index_template.html               # 메인 페이지
│   └── product_template.html             # 상품 상세
├── trend_finder.py                       # 메인 스크립트
├── seed_keywords.py                      # ⭐ 시드 키워드 (자체 포함)
├── data_collectors.py                    # 데이터 수집
├── product_analyzer.py                   # Claude API 분석
├── requirements.txt
└── README.md
```

---

## 업로드 절차 (15분, 코딩 몰라도 OK)

### 1) GitHub 가입 & 새 저장소

1. https://github.com → Sign up (이미 계정 있으면 로그인)
2. 우상단 `+` → `New repository`
3. **Repository name**: `trend-finder` (또는 원하는 이름)
4. **Public** 선택
5. README, .gitignore, license 모두 **체크 해제**
6. `Create repository`

### 2) 파일 업로드

방금 받은 zip 파일을 압축 해제하면 폴더가 나옵니다. 그 안에는:
- `.github` 폴더
- `templates` 폴더
- Python 파일 4개 (trend_finder, seed_keywords, data_collectors, product_analyzer)
- requirements.txt, README.md

GitHub 저장소 화면에서:
1. `uploading an existing file` 링크 클릭
2. 압축 푼 폴더 안의 **모든 항목을 한 번에** 드래그
3. 페이지 맨 아래 `Commit changes` 클릭

⚠️ `.github` 폴더가 함께 올라갔는지 확인. 안 올라가면 자동 실행 안 됩니다.
(만약 .github 폴더가 누락되면 별도로 `daily_trends.yml` 파일을 `.github/workflows/` 경로로 직접 만들어야 합니다)

### 3) GitHub Pages 활성화

저장소 메인 → `Settings` → 좌측 `Pages` → **Source: GitHub Actions** 선택.

### 4) Actions 권한 설정

`Settings` → `Actions` → `General` → 맨 아래 **Workflow permissions**:
- ⦿ **Read and write permissions** 선택
- `Save` 클릭

### 5) Claude API 키 등록 (필수)

이 시스템은 Claude API가 **반드시** 필요합니다. 시드 키워드만으로는 분석이 안 돼요.

**A. API 키 발급**
1. https://console.anthropic.com → API Keys → Create Key
2. 표시되는 키 즉시 복사 (`sk-ant-api03-...`)

**B. GitHub Secrets에 등록**
1. 저장소 `Settings` → `Secrets and variables` → `Actions`
2. `New repository secret`
3. **Name**: `ANTHROPIC_API_KEY` (정확히)
4. **Secret**: 위 키 붙여넣기
5. `Add secret`

**비용**: 매일 6회 API 호출 (선정 1회 + 상세 5회) × Claude Haiku 4.5 = 약 $0.05~0.10/일, 월 $1.5~3.

### 6) 첫 실행

저장소 상단의 `Actions` 탭 → `Daily Trend Finder` → `Run workflow` → `Run workflow` 클릭.

10~15분 대기. 완료되면 GitHub Pages URL에서 결과 확인.

이후 매일 새벽 7시(KST) 자동 실행됩니다.

---

## 솔직히 짚을 한계

### 1. TikTok/Pinterest 실시간 데이터 미포함
- TikTok Shop은 공식 API 없음 → Kalodata 같은 유료 도구 필요 (월 $99~)
- Pinterest Trends는 비즈니스 API 제한적

→ MVP에서는 Google Trends + Amazon + Etsy로 충분히 신호 잡힙니다.

### 2. 네이버/쿠팡 경쟁도 자동 검증 불가
- 한국 마켓플레이스는 봇 차단이 매우 강력해 자동 스크래핑 불가
- 후보 발굴 후 **사용자가 직접** 블랙키위·키워드마스터로 5분씩 검증

→ 시스템은 "후보 발굴" 단계까지. 한국 진입 결정은 사람이 하는 게 안전.

### 3. 자동 업로드는 의도적으로 미포함
- 인스타 자동 업로드는 계정 정지 위험
- **사용자가 최종 검수 후 수동 업로드** 권장

### 4. 데이터 수집 부분 실패 가능
- Amazon/Etsy는 봇 차단으로 가끔 실패
- 빌드는 계속 진행, 가능한 데이터로 분석

---

## 다음 단계 (선택)

이 시스템(Phase 1)에서 좋은 후보가 나오기 시작하면 Phase 2로 확장:

**Phase 2: 릴스 콘텐츠 생성기** (별도 시스템)
- 상품명 입력 → Claude가 릴스 대본/캡션/해시태그 생성
- FLUX/DALL-E로 목업 이미지 7장 생성
- CapCut으로 사용자가 10분 편집 (자동 MP4보다 품질 높음)

지금은 Phase 1만 가동해보시고 진짜 쓸만한 후보가 나오는지 검증부터 하세요.

---

## 면책

- 데이터: Google Trends · Amazon · Etsy 공개 데이터
- AI 분석: Claude Haiku 4.5
- **본 리포트는 사업 의사결정의 출발점이며 최종 판단은 본인의 추가 검증 후 이루어져야 합니다.**
- 예상 가격·마진은 추정치이며 실제와 다를 수 있습니다.
- 실제 진입 전 한국 검색량(블랙키위), 1688/알리바바 소싱, 샘플 발주 검증 필수.
