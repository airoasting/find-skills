# Skill Library

<a href="https://skill.airoasting.com/"><img src="docs/asset/og-image.svg" alt="AI Roasting · Skill Library (비즈니스 리더를 위해 엄선한 AI 스킬)" width="100%"></a>

비개발자 비즈니스 리더를 위해 큐레이션한 Claude 스킬·플러그인 카탈로그입니다. 현재 **150개 카드 · 3개 메타 카테고리 · 14개 세부 카테고리 · 28개 에디터픽**을 등록했고, 모든 데이터를 단일 파일 `skills.json`에서 관리합니다.

🌐 라이브 사이트: <https://skill.airoasting.com/>

## 무엇이 들어 있나

3개 메타 카테고리 아래 14개 세부 카테고리로 분류합니다. (괄호 안은 카드 수 · 에디터픽 수)

### 🏗 AI 에이전트팀 구축
나만의 AI 팀과 런타임을 직접 조립하고, AI와 더 잘 일하기 위한 협업 방식을 잡는 레이어입니다.

| 카테고리 | 무엇을 위한 것인가 | 카드 |
|---|---|---|
| 🛠 하네스 · 에이전트 설계 | 에이전트 팀과 런타임 구조를 직접 조립하는 플랫폼 레이어 | 19 (픽 4) |
| 🚀 AI와 일 잘하는 법 | 브레인스토밍·계획·기억·체크리스트 등 협업 습관 | 12 (픽 4) |
| ⚡ 토큰 절약 | 컨텍스트·토큰 사용량을 줄여 비용·속도 최적화 | 8 |
| 🤖 외부 연동 · 자동화 | 브라우저·메신저·이슈 트래커 등 외부 시스템 연결 | 15 (픽 2) |
| 🇰🇷 한국 특화 스킬 | 한글 문서·카카오·토스·네이버 등 국내 환경 | 10 (픽 1) |

### 📈 비즈니스 성장
매출·고객·자본 같은 성장 지표를 직접 움직이는 실험 도구입니다.

| 카테고리 | 무엇을 위한 것인가 | 카드 |
|---|---|---|
| 💼 그로스 · 마케팅 | CRO·카피·SEO·멀티채널 캠페인 실험 | 10 (픽 2) |
| 💹 투자 · 금융 | 트레이딩·포트폴리오·리서치 등 금융 업무 | 18 (픽 4) |
| 🔎 GEO · AEO | 생성형 AI 검색에서 브랜드·콘텐츠 인용 최적화 | 9 |

### 🎯 실행력 제고
리서치부터 디자인·동영상·글쓰기·법무·커리어까지 구체적 산출물을 빠르게 뽑는 도구입니다.

| 카테고리 | 무엇을 위한 것인가 | 카드 |
|---|---|---|
| 📊 리서치 · 인사이트 | 논문·지식그래프·딥리서치 등 깊이 있는 조사 | 18 (픽 3) |
| 🎨 디자인 | UI·슬라이드·디자인 시스템 등 시각 결과물 | 11 (픽 2) |
| 🎬 동영상 제작 | 편집·자막·모션 그래픽·영상 생성·더빙 | 7 (픽 2) |
| ✍️ 글쓰기 | 블로그·소설·에디팅·문서 작업 | 8 (픽 2) |
| ⚖️ 법무 · 컴플라이언스 | 계약·NDA·컴플라이언스 1차 스크리닝 | 3 (픽 1) |
| 🧭 커리어 · 이직 | 이력서·자소서·면접·지원 추적 | 2 (픽 1) |

- 카드별 정보: `repo`, `author`, `stars`, `forks`, `desc`(한국어 2문장), `tags`, `added_at`, 선택적으로 `lang`·`editors_pick`·`airoasting_lab`
- `meta_categories[]`·`categories[]` 정의에는 "이 카테고리는 어떤 일을 위한 것인가"가 한 줄로 들어 있어, 자연어로 골라 쓰기 좋습니다.

## 카드 둘러보기

가장 빠른 방법은 라이브 사이트입니다. 카테고리 칩에서 카드로, 다시 원 저장소로 바로 이동할 수 있습니다.

🌐 <https://skill.airoasting.com/>

URL 파라미터로 바로 들어갈 수도 있습니다.

| URL | 결과 |
|---|---|
| `?cat=workflow` | "AI와 일 잘하는 법" 카테고리만 |
| `?cat=korea` | "한국 특화 스킬"만 |
| `?cat=pick` | 에디터픽 28개만 |
| `?cat=lab` | AI Roasting이 직접 만든 자체 스킬 8개만 |

## 데이터 구조

```jsonc
{
  "authors": {
    "<owner>": { "facebook": "...", "linkedin": "...", "x": "..." }
  },
  "meta_categories": [
    { "id": "build", "name": "AI 에이전트팀 구축", "emoji": "🏗", "desc": "..." }
  ],
  "categories": [
    { "id": "workflow", "meta": "build", "name": "AI와 일 잘하는 법",
      "emoji": "🚀", "desc": "..." }
  ],
  "skills": [
    {
      "category": "workflow",
      "name": "Superpowers",
      "repo": "obra/superpowers",
      "author": "Jesse Vincent",
      "stars": 240748,
      "forks": 21376,
      "desc": "이 스킬은 ... 입니다. ... 때문에 ...에 적합합니다.",
      "tags": ["#workflow-engine", "#tdd", "#brainstorming"],
      "lang": "Shell",
      "added_at": "2025-10-09",
      "editors_pick": true
    }
  ]
}
```

`docs/skills.json`이 단일 진실 공급원이지만, 정적 호스팅(`file://` 직접 열기) 환경을 위해 `docs/index.html` 안에 동일 JSON이 인라인으로 박혀 있습니다. 두 곳을 같이 갱신해야 합니다 ([docs/app.js:50](docs/app.js:50) 폴백 로직 참고).

## 프로젝트 레이아웃

웹 번들은 GitHub Pages `/docs` 서빙을 위해 `docs/`에 있습니다.

```
.
├── docs/                   # GitHub Pages 서빙 루트
│   ├── index.html          # 카탈로그 페이지 (인라인 skills-data 포함)
│   ├── app.js              # 검색·필터·URL 라우팅
│   ├── skills.json         # 데이터 단일 소스
│   ├── asset/              # OG 이미지·로고·Pretendard 폰트
│   └── .nojekyll           # GitHub Pages Jekyll 처리 비활성화
└── scripts/
    ├── sync-stars.py       # GitHub 별·포크 수 동기화
    └── sync-inline.py      # docs/skills.json → docs/index.html 인라인 블록
```

## 로컬에서 보기

별도 빌드 단계가 없습니다.

```bash
# 가장 간단: file://로 직접 열기 (인라인 폴백 사용)
open docs/index.html

# 또는 정적 서버 (docs/ 를 루트로)
python3 -m http.server 8000 --directory docs
# → http://localhost:8000
```

## 카드를 제안하고 싶다면

추천 후보가 있으면 [Issue](https://github.com/airoasting/skill_library/issues/new)를 열어 GitHub 주소·카테고리 후보·한 줄 추천 사유를 남겨주세요. 큐레이터가 직접 검토 후 라이브러리에 반영합니다.

## 라이선스

스킬 카드의 메타데이터는 라이브러리 운영을 위한 큐레이션입니다. 각 스킬의 코드와 라이선스는 원 저장소를 따릅니다.
