<a href="https://skill.airoasting.com/"><img src="docs/asset/og-image.svg" alt="AI Roasting · Skill Library (비즈니스 리더를 위해 엄선한 AI 스킬)" width="100%"></a>

# find-skills

**v1.2.1** · MIT · Claude Code, Codex

"회의록 정리하는 스킬 있어?" 하고 물으면 쓸 만한 스킬을 찾아 직접 열어 본 뒤 추천하고, 원하면 설치까지 해 주는 에이전트 스킬입니다.

쓸 만한 스킬은 대개 누군가 이미 만들어 두었습니다. 어려운 건 그걸 찾는 일, 그리고 찾은 스킬을 믿어도 되는지 가리는 일입니다. find-skills는 이 두 가지를 맡습니다.

## 이렇게 찾습니다

먼저 이미 깔려 있는 스킬부터 봅니다. 거기서 해결되면 새로 깔 이유가 없습니다. 없으면 비즈니스 리더용으로 골라 둔 [AI Roasting 스킬 라이브러리](https://skill.airoasting.com/)를 보고, 그래도 없으면 오픈 생태계인 [skills.sh](https://skills.sh/)까지 넓혀 찾습니다.

후보가 나와도 바로 권하지 않습니다. 저장소를 열어 SKILL.md 본문과 스크립트를 읽고, 복사본은 아닌지, 설치하고 나서 따로 챙길 준비물(API 키나 별도 프로그램 같은)은 없는지, 위험한 코드는 없는지, 설치 명령이 실제로 통하는지를 확인합니다. 무엇을 보고 그렇게 판단했는지는 파일의 몇 번째 줄인지까지 함께 보여 줍니다.

추천은 3개 안팎으로 추립니다. 설치는 사용자가 분명히 원할 때만 합니다.

## 설치

**Claude Code 플러그인**

```
/plugin marketplace add airoasting/skills
/plugin install find-skills@airoasting
```

**skills CLI (Claude Code, Codex)**

```bash
npx skills add airoasting/find-skills -g -a claude-code
```

Codex에서 쓰려면 `-a codex`로 바꿔 주세요. 설치한 다음에는 새 세션을 열어야 스킬이 잡힙니다.

**업데이트**

```bash
claude plugin marketplace update airoasting && claude plugin update find-skills@airoasting   # 플러그인
npx skills update                                                                            # skills CLI
```

Python 3.9 이상이 있어야 하고, Node.js는 설치할 때만 씁니다. skills.sh와 GitHub을 조회하니 네트워크도 필요합니다. `gh` CLI는 없어도 됩니다. Codex는 기본 샌드박스가 네트워크를 막아 두어서, 스킬이 돌 때 네트워크를 써도 되는지 물어봅니다.

## 쓰는 법

이런 식으로 물으면 알아서 나섭니다. 이름을 불러 시킬 수도 있습니다.

- "회의록 정리해서 액션 아이템까지 뽑아 주는 스킬 있어?"
- "한글(HWP) 문서 고칠 수 있는 스킬 찾아줘"
- "next.js LCP 개선하는 데 뭐 깔면 돼?"
- `/find-skills 계약서 검토`

HWP 질의에 실제로 나온 답을 줄여 옮기면 이렇습니다.

```
이해한 작업: 공공기관 제출용 .hwp를 읽고 .hwp 그대로 고쳐 저장하는 스킬을 찾습니다.
검색 범위: 설치된 스킬 58개 중 HWP 관련 0개 → AI Roasting 라이브러리 150개 중 --grep hwp와 korea 카테고리
          (맞는 것 1개, 일부만 맞는 것 2개) → skills.sh 후보 16개 훑음 → 본문 확인 5개 → 추천 2개
본문 확인 후 뺀 것: rhwp(직접 빌드 필요), K-Skill hwp(읽기 전용, 1번과 겹침), HWPX Skill(.hwpx 전용)

### 1. Kordoc  ·  AI Roasting 라이브러리
...

### 2. rhwp-edit  ·  AI Roasting 라이브러리(K-Skill 안의 스킬)
- 무엇: .hwp를 .hwp 그대로 고칩니다. 수정 전용입니다.
- 신뢰: ★7,820(모음 전체 기준) · 5,290 installs · 저장소 최근 갱신 2026-10
- 한계: 실행할 때 원격 패키지에서 지시를 받아 오므로 설치 뒤 지시가 바뀔 수 있습니다.
- 설치: npx skills add NomaDamas/k-skill --skill rhwp-edit -g
- 준비물: 필수 Node.js 18+ / 선택 rhwp-advanced 스킬(배포용 문서 잠금 해제)

1, 2번을 함께 설치할까요? 모든 프로젝트에서 쓰도록 전역으로 넣습니다.
```

## 단계별로 보면

```
1. 필요 읽기   작업 의도, 산출 형식(.pptx, .hwp 등), 제약, 개발 작업인지 판단. 영문 검색어 2~4개를 만듦
2. 설치된 것   지금 에이전트에 깔린 스킬로 되면 여기서 끝
3. 라이브러리  AI Roasting 카드에서 찾음
4. skills.sh   여러 검색어를 병렬로 검색. 설명을 붙이고, 걸린 질의 수 순으로 정렬
5. 확인        최종 후보 3~5개를 저장소를 받지 않고 검증
6. 추천        검색 범위 한 줄, 후보마다 고른 이유·한계·설치 명령·준비물
7. 설치        사용자가 승낙한 뒤에만
```

5단계에서는 후보마다 이런 걸 따집니다.

| 따지는 것 | 이런 스킬은 걸러 냅니다 |
|---|---|
| 하는 일 | 이름은 그럴듯한데 본문은 딴 일을 하는 스킬, 결과물 형식이 다른 스킬. 껍데기(스텁)만 있는 스킬은 실제 지시 파일까지 열어 봅니다 |
| 신뢰 | 설치 수에 비해 별이 너무 적은 복사본, 남의 스킬을 설치본 경로에 들여놓은 사본, 다른 곳으로 옮겨 갔거나 폐기된 저장소, 오래 방치된 저장소 |
| 안전 | 자격 증명을 건드리거나 원격 스크립트를 바로 실행하는 스킬, 실행할 때마다 지시를 받아 오거나 다른 스킬까지 깔고 업데이트하는 스킬 |
| 사용자에게 맞는지 | 개발자가 아닌 리더에게 권하기 어려운 개발 전용 도구 |
| 준비물 | 설치 명령 말고도 런타임, API 키, 별도 프로그램, MCP 서버, 유료 플랜이 필요한 경우. 필수와 선택을 나누고 근거 줄을 붙여 보여 줍니다 |
| 언어와 발동 | 결과물 양식이 다른 언어로 고정된 스킬, 자동 발동이 꺼져 있는 스킬 |
| 설치 | 그대로 치면 실패하는 명령, 원치 않는 스킬 수십 개를 한꺼번에 까는 묶음 플러그인, skills CLI로 깔면 빠져 버리는 MCP 서버 |

스크립트가 하는 일은 근거를 모으는 데까지입니다. 어떤 스킬이 맞는지는 그 출력을 읽은 에이전트가 정합니다.

## 파일 구성

```
SKILL.md                         # 7단계 절차, 판단 기준, 출력 양식
.claude-plugin/plugin.json       # 플러그인 이름·버전
scripts/                         # 표준 라이브러리만 쓰는 Python
├── find_installed.py            # 2단계: 설치된 스킬을 에이전트별로, 이름과 설명으로
├── find_library.py              # 3단계: 라이브러리 카드 (--cat, --grep)
├── find_search.py               # 4단계: skills.sh 병렬 검색, 요청 한도 구분, 동명 복사본 묶음
├── find_inspect.py              # 5단계: 설치 방법, 준비물, 신뢰·위험 신호, 본문 (--show로 근거 줄 열기)
├── check_release.py             # 스킬을 고쳤는데 버전을 안 올렸으면 커밋을 막음
└── sync-inline.py, sync-stars.py  # 카탈로그 운영용
evals/
├── evals.json                   # 테스트 질의 6개와 채점 기준
└── test_inspect_patterns.py     # 스크립트 판정 회귀 검사 (네트워크 없이)
docs/                            # AI Roasting 스킬 라이브러리 웹 사이트 (3단계의 데이터 소스, 로컬 사본)
```

설치하면 저장소가 통째로 들어옵니다. 약 17MB인데 대부분 `docs/`에 든 사이트 이미지입니다. 스킬이 실제로 쓰는 파일은 그중 `SKILL.md`, `scripts/find_*.py`, `docs/skills.json` 정도입니다.

## 어떻게 검증했나

성격이 다른 질의 4개(회의록, HWP, Next.js, 이사회 PPT)는 Claude Code에서, 2개(HWP, PPT)는 Codex에서 처음부터 끝까지 돌려 보고 채점합니다. v1.2.0을 마무리하며 돌린 마지막 회차에서는 Claude Code 61/61, Codex 21/21로 채점 기준을 모두 통과했습니다(2026-10-09).

그 과정에서 한 번이라도 틀렸던 사례 124건은 회귀 검사로 묶어 두었습니다. 스크립트를 손봤다면 아래 명령으로 돌려 보면 됩니다.

```bash
python3 evals/test_inspect_patterns.py
```

## 변경 내역

- **1.2.1** (2026-10-09) SKILL.md를 저장소 맨 위로 옮겨 AI Roasting의 다른 스킬 저장소와 구조를 맞췄습니다. 라이선스는 MIT로 정했습니다.
- **1.2.0** (2026-10-09) 실사용 테스트를 네 번 돌리면서 다듬은 판입니다. 설치된 스킬 확인, 검색 결과의 설명과 정렬, 근거를 보여 주는 준비물 판정, 복사본·스텁·이전 판정, `--show`, Codex 지원이 이때 들어갔습니다.
- **1.1.0** (2026-10-08) 스킬을 하위 폴더로 옮겨 설치 크기를 줄였고, 버전을 올리지 않으면 커밋을 막는 릴리스 점검을 넣었습니다.

## 아직 부족한 점

- 어떤 질문에 이 스킬이 불리고 어떤 질문에는 안 불리는지, 발동 정확도는 아직 재 보지 않았습니다.
- 준비물과 위험 신호는 문서와 코드를 패턴으로 훑어서 찾습니다. 문서에 안 적힌 건 못 찾으니, 판정으로 받아들이기보다 먼저 읽어 볼 곳으로 보는 게 맞습니다.
- 복사본을 가르는 기준(별 1개당 설치 1,000회 초과)은 2026년 10월에 잰 값으로 정했습니다. 짧은 시간에 빠르게 퍼진 신생 저장소는 복사본으로 잘못 걸릴 수 있습니다.
- 설치 수는 skills.sh에 올라간 스킬만 알 수 있습니다.

## 고쳐서 내보낼 때

플러그인으로 깐 사람은 **버전 번호가 올라가야** 새 버전을 받습니다.

1. `SKILL.md`나 `scripts/find_*.py`를 고친 다음 `.claude-plugin/plugin.json`의 `version`을 올립니다(작은 수정은 1.2.1 → 1.2.2, 기능 추가는 1.3.0).
2. `python3 evals/test_inspect_patterns.py`와 `claude plugin validate .`로 점검합니다.
3. 커밋합니다. 버전을 안 올렸으면 pre-commit 훅이 커밋을 막습니다. 배포할 필요가 없는 변경이면 `SKIP_RELEASE_CHECK=1 git commit ...`으로 넘어갑니다.
4. `claude plugin tag .`로 태그를 만들고 `git push --tags`로 올립니다.

## 데이터 소스: AI Roasting 스킬 라이브러리

find-skills가 3단계에서 가장 먼저 들여다보는 카탈로그입니다. 개발자가 아닌 비즈니스 리더를 염두에 두고 고른 Claude 스킬·플러그인 150개를 14개 카테고리로 나눠 담았고, 그중 28개가 에디터픽입니다. 사람이 직접 둘러보려면 <https://skill.airoasting.com/>에 들어가면 됩니다. 주소 뒤에 `?cat=korea`(한국 특화)나 `?cat=pick`(에디터픽)을 붙이면 그 목록으로 바로 갑니다.

카드 데이터의 원본은 `docs/skills.json` 하나입니다. `docs/index.html` 안에 든 인라인 사본은 커밋할 때 pre-commit 훅이 `scripts/sync-inline.py`로 맞춰 줍니다. 사이트를 로컬에서 띄워 보려면 `python3 -m http.server 8000 --directory docs`를 실행하면 됩니다.

추천하고 싶은 스킬이 있으면 [Issue](https://github.com/airoasting/find-skills/issues/new)에 GitHub 주소와 카테고리 후보, 추천하는 이유 한 줄을 남겨 주세요.

## 라이선스

find-skills는 [MIT](LICENSE) 라이선스입니다. 라이브러리 카드에 실린 스킬의 코드와 라이선스는 각 원 저장소를 따릅니다.
