# MEMORY.md, 운영 결정 로그

이 문서는 스킬 라이브러리의 운영 결정이 **왜** 내려졌는지 기록한다. 규칙 자체는 `AGENTS.md`가 정본이고, 여기는 그 규칙의 배경과 경위, 그리고 아직 정리되지 않은 미결 사항을 남긴다.

## 사용법

- 규칙이 생기거나 바뀔 때, 카드가 일괄로 움직일 때, 같은 커밋에서 아래에 항목을 추가한다.
- 형식: 날짜, 무엇을 결정했나, 왜, 남은 일. 최신이 위로 온다.
- 개별 카드 1개 추가·제거는 git 히스토리로 충분하므로 여기 적지 않는다. 여기는 **방향이 바뀐 순간**만 기록한다.

## 결정 기록

### 2026-10-03. `video`(동영상 제작) 카테고리 신설, 7개 입고·7개 제거

- **무엇**: 실행력 제고 메타의 디자인 바로 다음에 `video`(🎬 동영상 제작) 카테고리를 만들고 HyperFrames, Video Use, OpenMontage, Open Edit, Higgsfield Skills, Remotion Skills, Violin 7개를 넣었다. 150 유지를 위해 서드파티 별점 최하위 7개(Codex Insane Search, AI Co-Writing System, Design Research, ultimate-seo-geo, aeo.js, Awesome Novel Studio, Awesome Ad Video Prompts)를 뺐다. 세부 카테고리는 13개에서 14개가 됐다.
- **왜**: 영상 편집·자막·더빙을 에이전트에 맡기는 스킬이 별점 1천 이상 규모로 쌓였고, 기존 디자인 카테고리(UI·슬라이드)로는 담을 수 없었다.
- **컷 기준**: 사용자 결정으로 ★1,000 미만은 제외했다. 그래서 3축 평균 4.0이던 HeyGen Skills(461★, 공식 조직)와 3.7이던 claude-youtube(413★)는 빠졌다. Remotion Skills는 React 프로젝트를 전제하는 개발자 지향이라 게이트 3 경계였지만, 공식 저장소이고 평균 4.0이라 넣었다.
- **제외 근거**: OpenCreator는 Codex 기반 데스크톱 앱, brag·guizang-product-video는 코드 저장소 전제, claude-code-video-toolkit은 클라우드 GPU 직접 구성 필요, drama-skills는 중국 숏드라마 실무자용, Premiere MCP 계열은 게이트 4로 탈락했다.
- **에디터픽**: HyperFrames·Video Use(평균 4.7)는 사용자 승인을 받아 `editors_pick: true`로 달았다. 에디터픽은 26개에서 28개가 됐다.
- **남은 일**: Awesome Ad Video Prompts는 영상 광고 프롬프트라 video와 맞았지만 별점 규칙대로 제거했다. 1천 미만 공식 저장소(HeyGen Skills)를 예외로 받을지는 미결이다.

### 2026-07-17. 운영 문서 체계 재편

- **무엇**: `AGENTS.md`(운영 기준 정본)와 `MEMORY.md`(이 문서)를 신설하고, `CLAUDE.md`는 `AGENTS.md`로 안내하는 리다이렉트로 전환했다.
- **왜**: 카드 선정 기준이 구 `CLAUDE.md`(150 룰·제거 기준), `.claude/commands/add-skill.md`(입고 게이트·에디터픽), `.claude/commands/discovery-skill.md`(발굴 평가)에 흩어져 있었다. 기준이 세 곳에 나뉘면 어긋나기 시작하고, Claude 외의 도구(Codex 등)는 CLAUDE.md라는 파일명을 읽지 않는다. 도구 중립 파일명 하나에 기준을 모았다.
- **원칙**: 규칙은 AGENTS.md 한 곳, 절차는 커맨드 파일, 배경은 MEMORY.md. 같은 내용을 두 곳에 적지 않는다.

### 2026-07-17. 대체 카드 25개 입고, 150 복원

- **무엇**: MCP 삭제로 125가 된 라이브러리에 discovery 기준을 통과한 신규 카드 25개를 넣어 150을 복원했다. 카테고리별로 automation 3, design 4, token 3, korea 2, finance 4, research 4, business 2, writing 1, workflow 2다.
- **왜 이 분포인가**: 삭제는 korea 8·automation 7에 몰렸지만, 별점 500 이상 비-MCP 스킬의 실제 고품질 공급은 research·design에 몰려 있었다. 니치(korea·automation)를 억지로 맞추려면 기준을 깨야 해서, "분포 복원"보다 "카테고리별 최고 품질"을 택했다. 결과적으로 korea 16→10, research 17→18로 재편됐다.
- **경계 판단 2건**: ① research의 Obsidian 계열이 겹쳐 Obsidian Second Brain(3.7)을 빼고 korea의 HWPX Skill(Canine89, 273★)로 교체했다. korea 니치의 별점 상한(최고 518★)이 낮아 3.5 컷 통과가 Docufinder 하나뿐이라, HWPX Skill은 신뢰성 축 미달(273★)이지만 효용성·대표성이 높아 예외로 넣었다. ② cowork-plugins(254★)는 한국 B2B 마켓플레이스로 매력적이나 NC-ND(상업 이용 금지) 라이선스라 제외했다.
- **발굴 방식**: 도메인별 서브에이전트 6개를 병렬로 돌려 각자 gh search + README 실독으로 3축 평가. automation 담당은 대형 awesome 리스트 순회로 1회 타임아웃 실패 후 재시도로 복구했다.
- **에디터픽**: 신규 25개는 모두 editors_pick 생략(false). Agent Reach·Guizang·ccusage·Knowledge Work Plugins 등 평균 5.0 후보가 있으나, 게이트 5는 사용자 승인이 필요하므로 이번엔 배지를 달지 않았다. 승인 절차는 추후 별도로.
- **남은 판단거리**: automation은 향후 보충 시 별점 기준을 낮추거나(300+) "소셜 발행·모니터링" 세부 축을 따로 잡지 않으면 6개 채우기 어렵다.

### 2026-07-17. 카테고리 설명·README의 MCP 문구 정리

- **무엇**: MCP 금지 정책에 맞춰 `automation` 카테고리 name("외부 연동 · MCP"→"외부 연동 · 자동화")과 desc, `korea` name("한국 특화 스킬 · MCP"→"한국 특화 스킬")과 desc에서 MCP 문구를 제거했다. README.md의 "스킬·플러그인·MCP 카탈로그" 문구와 카테고리별 카드 수·에디터픽 수(150개, 26개)도 실제 값으로 갱신했다.
- **왜**: 카드에서 MCP를 빼는데 카테고리 이름과 소개 문구가 여전히 MCP를 내세우면 정책과 표면이 어긋난다.
- **남은 일**: `docs/asset/og-image.svg`에 MCP 관련 문구가 있는지 미확인. 있으면 갱신 필요.

### 2026-07-17. MCP 서버 카드 전량 삭제, 신규 입고 금지

- **무엇**: MCP 서버 카드 25개를 일괄 삭제했다(150 → 125). 이름·저장소에 MCP가 들어간 21개와, 이름에는 없지만 설명이 "이 MCP는"으로 시작하는 사실상의 MCP 서버 4개(Context Mode, code-review-graph, Token Savior, claude-context)가 대상이다. 이후 MCP 서버는 입고 게이트에서 원천 제외한다(AGENTS.md 게이트 4).
- **왜**: 사용자(큐레이터) 결정. 이 라이브러리는 "골라서 바로 쓰는 스킬·플러그인" 카탈로그인데, 서버 설치·구성이 필요한 MCP는 비개발자 리더의 사용 장면과 맞지 않는다.
- **경계 판단**: MCP가 부가 기능인 하이브리드 3개(RuFlo, GBrain, Kordoc)는 유지했다. 기준은 "MCP를 빼도 카드의 가치가 성립하는가"였고, 셋 다 성립한다.
- **부수 정리**: 삭제로 고아가 된 `authors.hollobit` 엔트리를 제거했다.
- **남은 일**: 새 카드 25개를 채워 150을 복원한다(사용자 확정). 후보는 discovery 기준으로 발굴 중이며, 삭제된 카테고리 분포(korea 8, automation 7, finance 5, research 3, token 1, design 1)를 참고하되 그대로 맞출 의무는 없다.

### 2026-07-05 이전. 150개 총량 룰과 제거 기준 (구 CLAUDE.md에서 승계)

- **무엇**: 카드 총량 150 고정. 추가 시 반드시 하나 제거. 제거는 airoasting/* 보호, 별점 최하위 우선, 동점이면 fork 낮은 쪽, 애매하면 사용자 확인.
- **왜**: 총량 제한이 없으면 큐레이션이 수집으로 변질된다. 상한이 "기존 카드보다 나은가"라는 비교를 강제한다. airoasting/*는 운영자의 자체 자산이라 별점 잣대를 적용하지 않는다.

### 2026-07-05 이전. 입고 게이트와 에디터픽 3축 (add-skill에서 정립)

- **무엇**: 중복 검사, 카테고리 검증, 비즈니스 리더 적합성 게이트, 에디터픽 3축(효용성·대표성·신뢰성, 평균 4.0+, 의심스러우면 탈락)을 add-skill 커맨드에 정립했다.
- **왜**: 별점만 보고 받으면 개발자 전용 도구가 섞인다(스타 높은 개발자 전용 저장소가 실제로 있었다). 에디터픽은 흔해지면 배지 가치가 사라지므로 기본 생략에 사용자 승인제로 묶었다.

## 미결 사항

- [x] ~~**150 복원**~~: 완료(2026-07-17). AGENTS.md 8절 검증 통과, 총량 150.
- [x] ~~**카테고리 설명의 MCP 문구**~~: 완료(2026-07-17). automation·korea name/desc, README 문구 갱신.
- [x] ~~**README 통계 갱신**~~: 완료(2026-07-17). 카테고리별 카드 수·에디터픽 수(26개) 갱신.
- [ ] **OG 이미지 문구**: `docs/asset/og-image.svg`에 "MCP" 관련 문구가 있는지 미확인. 있으면 정책에 맞게 갱신.
- [ ] **신규 카드 별·포크 동기화**: 25개 카드의 stars는 발굴 시점 근사치. `scripts/sync-stars.py`를 한 번 돌려 정확한 값과 forks를 채우는 것이 좋다.
- [ ] **에디터픽 재평가**: 신규 25개 중 평균 5.0급(Agent Reach·Guizang·ccusage·Knowledge Work Plugins 등)은 게이트 5 승인 시 editors_pick 부여 검토.
