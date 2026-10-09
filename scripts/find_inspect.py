#!/usr/bin/env python3
"""find-skills 5단계: 후보 스킬 하나를 저장소 전체를 내려받지 않고 검증한다.

스크립트는 근거를 모아 줄 번호와 함께 보여 줄 뿐 판정하지 않는다. 최종 판단은 출력을 읽은
에이전트가 한다. 패턴으로 '필수'를 단정하면 틀린다는 것을 실사용에서 확인했다(선택 항목을 필수로,
코드 상수를 API 키로 읽었다). 그래서 준비물은 두 층으로 낸다.
  1차 근거: 본문이 스스로 밝힌 준비 절(Prerequisites, Requirements, 설치, 环境要求 등)의 원문
  2차 후보: 패턴으로 찾은 것. 항목마다 파일:줄과 '선택' 표지, 스킬이 실제로 부르는 파일인지를 붙인다

출력 순서:
  저장소 메타 → 스킬(라이브러리 카드 여부) → 설치 방법 → 설치 외 준비물 → 발동·언어 → 신뢰 신호
  → 위험 신호 → (스텁이면) 실제 지시 파일 → SKILL.md 본문

사용법:
  python3 scripts/find_inspect.py anthropics/skills@pdf
  python3 scripts/find_inspect.py owner/repo@skill --lines 200
  python3 scripts/find_inspect.py browser-use/video-use      # 저장소 맨 위 SKILL.md를 기본으로 고른다
  python3 scripts/find_inspect.py owner/repo@skill --installs 2908   # 4단계에서 본 설치 수를 넘기면 조회 1회를 아낀다

GitHub 메타와 파일 목록은 gh CLI(로그인돼 있으면)나 GitHub 공개 API(시간당 60회)로 읽는다.
파일 본문은 raw 주소로 받아 API 한도를 쓰지 않는다. 한 번 검증에 API를 2~3회 쓴다.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import posixpath
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True  # 설치된 스킬 폴더에 __pycache__를 남기지 않는다
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from find_search import search  # noqa: E402  같은 폴더의 skills.sh 검색

RISK = [
    (r"(curl|wget)[^\n|]*\|\s*(ba|z)?sh", "원격 스크립트를 내려받아 바로 실행"),
    # 디코딩 자체는 이미지·폰트 처리에서 흔하다. 풀어낸 것을 바로 실행할 때만 잡는다.
    (r"(exec|eval|Function)\s*\([^)\n]{0,80}(b64decode|atob|base64)"
     r"|base64\s+(-d|--decode)[^\n]*\|\s*(ba|z)?sh", "인코딩된 내용을 풀어 실행"),
    (r"~/\.ssh|id_rsa|\.aws/credentials|\.netrc|keychain|security find-", "자격 증명 파일 접근"),
    (r"(API_KEY|SECRET|TOKEN|PASSWORD)[^\n]{0,80}(curl|requests\.|fetch\(|http)", "API 키·비밀값을 쓰는 외부 호출(어느 서비스로 가는지 확인)"),
    (r"rm\s+-rf\s+(~|/|\$HOME)", "광범위한 삭제"),
    (r"\bsudo\b", "관리자 권한 요구"),
    (r"dangerously[-_ ]?(skip|disable|bypass)|--no-verify|bypass ?permissions", "안전장치 우회"),
    (r"ignore (all )?(previous|prior) instructions", "프롬프트 주입 문구"),
    # 설치 뒤에 내용이 바뀌는 구조. 지금 읽은 본문과 실제로 실행되는 지시가 다를 수 있다(K-Skill에서 확인)
    (r"\b(?:npx|uvx|bunx|pipx run)\s+(?:-y\s+|--yes\s+)?@?[\w./-]+(?:@[\w.^~-]+)?\s+(?:instruct|instructions|prompt|guide)\b",
     "실행할 때 원격 패키지에서 지시를 받아 옴"),
    (r"\b(?:update|upgrade)\b[^\n]{0,60}\b(?:every|all)\b[^\n]{0,40}\bskills?\b|\bskills\s+(?:update|upgrade)\b"
     r"|\b(?:npx|uvx|bunx)\s+(?:-y\s+|--yes\s+)?@?[\w./-]*skill[\w./-]*(?:@[\w.^~-]+)?\s+(?:update|upgrade|self-update)\b"
     r"|\b(?:every|all)\b[^\n]{0,30}\bskill install",
     "다른 스킬까지 일괄 업데이트"),
    (r"check[_-]?(?:latest|for)[_-]?(?:version|update)s?|\b(?:before|after) (?:every|each) (?:final )?(?:reply|response|request)\b",
     "사용할 때마다 버전 확인 등 외부 호출을 실행"),
]
SCRIPT_EXT = (".sh", ".py", ".js", ".ts", ".mjs", ".cjs", ".rb", ".ps1")
# 저자가 쓴 코드가 아니라 함께 들어 있는 라이브러리·빌드 결과물. 압축된 한 줄짜리 코드라 패턴 검사가
# 오탐(React의 dangerouslySetInnerHTML, 브라우저의 atob 등)만 내고, 검사 한도를 먼저 채워 저자의
# 스크립트를 밀어낸다. 그래서 검사에서 빼고 개수만 알린다.
BUNDLED = re.compile(r"(^|/)(vendor|vendors|dist|build|node_modules|third_party)/"
                     r"|[.-]min\.(js|css)$|\.(umd|bundle|chunk)\.js$")
MAX_SCAN = 200         # 검사할 저자 스크립트 수 상한. raw 주소로 받아 API 한도를 쓰지 않는다
MAX_BYTES = 200_000    # 이보다 큰 파일은 사람이 쓴 스크립트가 아닐 가능성이 크다
TARGET = re.compile(r"^[\w.-]+/[\w.-]+(@[\w.:+-]+)?$")

# 설치 수 대비 별. 2026-10 skills.sh에서 잰 값: 정상 스킬은 별 1개당 설치 5~175회
# (anthropics/skills 5, vercel-labs/agent-skills 24, pexoai 50, pilioai 172). 복사본·부풀린 설치 수는
# 1,000회를 크게 넘었다(101-skills/superpowers@ai-video-generation 별 5·설치 70만 = 14만 회,
# hexiaochun/seedance2-api 별 3·설치 1.2만 = 4천 회). 설치 수가 작으면 비율이 흔들리니 하한을 둔다.
INFLATED_RATIO = 1_000
INFLATED_MIN = 5_000
COLLECTION = 5         # 저장소에 스킬이 이만큼 이상이면 별은 모음 전체의 수로 읽는다
# 에이전트가 스킬을 설치하는 위치. 저장소의 이 경로에 있는 스킬은 다른 곳에서 가져다 둔 사본일 수 있다
# (vercel-labs/openreview의 .agents/skills/next-best-practices에서 확인)
VENDORED = re.compile(r"^(?:\.agents|\.claude|\.cursor|\.codex|\.windsurf|\.gemini|\.github)/skills/")
# 이전·폐기 표시. 모음 저장소 README 깊은 곳의 무관한 문장을 잡지 않도록 README 앞 60줄과 SKILL.md 앞 30줄만 본다
MOVED = re.compile(r"\b(?:deprecated|no longer (?:maintained|supported|a skill|updated|available)|(?:has|have) (?:been )?moved"
                   r"|moved to|new home|superseded by)\b|더 이상 (?:관리|지원|유지)|이전했|폐기", re.I)

# ---- 설치 외 준비물 ----
# 1차 근거: 본문이 스스로 밝힌 준비 절의 제목
# 제목이 이 말로 시작할 때만 준비 절로 본다("Output Requirements" 같은 제목은 준비 절이 아니다)
PREREQ_HEAD = re.compile(r"^[\W\d_]*(?:[A-Za-z][.)]\s*)?(?:prereq\w*|first\b[^\n]{0,40}\b(?:verify|check|install|tools?)\b|(?:system )?requirements?\b|dependenc\w*|before you (?:begin|start)|getting started"
                         r"|set ?up\b|installation|install\w*|quick ?start|환경|준비|사전 준비|요구 ?사항|필요한 것|설치|依赖|环境|安装|前置)", re.I)
FM_KEYS = re.compile(r"^(mcp|mcpServers|requires|dependencies|compatibility|environment|runtime|allowed-tools)\s*:", re.I)
OPTIONAL = re.compile(r"\boptional\b|only if|only needed|if needed|if (?:it|that|the \w+) fails|\bfallback\b|not required|edge[- ]case"
                      r"|(?:don't|do not|doesn't) need|필요할 때만|경우에만"
                      r"|선택|필요하면|필요한 경우|원하면|없어도|可选|仅在|无需|不需要|若需", re.I)
# 비밀값 이름. 문서에서는 이름만으로, 스크립트에서는 환경 변수로 읽을 때만 잡는다(코드 상수 CERT_KEY 같은 오탐 방지)
SECRET_VAR = re.compile(r"\b(?!YOUR_)[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_(?:API_KEY|KEY|TOKEN|SECRET|SECRET_KEY|ACCESS_KEY)\b")
ENV_ACCESS = re.compile(r"(?:process\.env\.|process\.env\[['\"]|os\.environ(?:\.get)?\s*[\[(]\s*['\"]|getenv\(\s*['\"]"
                        r"|ENV\[['\"]|\$\{?)([A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET)[A-Z0-9_]*)")
ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]{2,})\s*=", re.M)
NOT_SECRET_LINE = re.compile(r"redact|\bmask|\[REDACTED\]|never (?:put|commit|log|share|print)|do not (?:commit|share|log|print)"
                             r"|\.replace\(|placeholder", re.I)
RUNTIME = {
    "Node.js": r"\bnode(?:\.js)?[*\s]*(?:v|>=?\s*)?\d{2}(?:\.\d+)*\+?|\bnpx\s+(?:-y\s+|--yes\s+)?(?!skills\b)@?[\w.-]+[\w./@^~-]*"
               r"|\bnode\s+[\w./-]+\.(?:m?js|cjs)\b|\bnpm\s+(?:install|i|ci|run)\b",
    "Python": r"\bpython[*\s]*3\.\d+\+?|\bpython3?\s+(?:-m\s+[\w.]+|[\w./-]+\.py)\b|\bpip3?\s+install\b|\buv\s+run\b",
    "uv": r"\buv\s+(?:sync|run|tool|pip|add)\b|\buvx\b",
    "Bun": r"\bbunx?\s+(?:install|run|x)\b",
    "Deno": r"\bdeno\s+(?:run|install|task)\b",
    "Rust(cargo)": r"\bcargo\s+(?:install|build|run)\b",
}
VERSION = re.compile(r"node(?:\.js)?[*\s]*(?:v|>=?\s*)?(\d{2}(?:\.\d+)?\+?)|python[*\s]*(3\.\d+\+?)", re.I)
# 부정문("python -m http.server는 쓰지 않는다")의 도구 이름은 준비물이 아니다
NEGATED = re.compile(r"\b(?:don't|do not|never|instead of|avoid|without|not)\b|쓰지 않|쓰지 말|대신|불필요|필요 없"
                     r"|不要|不用|不得|无需|勿|禁止|别用|而不是", re.I)
# SKILL.md 코드 블록의 import. 표준 라이브러리는 빼고 나머지를 Python 패키지 후보로 본다
PY_IMPORT = re.compile(r"^\s*(?:from\s+([a-zA-Z_]\w*)[\w.]*\s+import|import\s+([a-zA-Z_]\w*))")
STDLIB = set("""os sys json re pathlib subprocess datetime typing collections math time csv glob shutil argparse itertools
functools io tempfile base64 random string textwrap urllib uuid hashlib logging dataclasses enum copy pprint zipfile
statistics decimal fractions html xml http email socket threading asyncio concurrent contextlib traceback warnings
inspect operator struct calendar locale unicodedata gzip tarfile sqlite3 platform signal queue heapq bisect abc""".split())
PY_PACKAGE = {"pptx": "python-pptx", "docx": "python-docx", "fitz": "PyMuPDF", "PIL": "Pillow", "cv2": "opencv-python",
              "yaml": "PyYAML", "bs4": "beautifulsoup4", "sklearn": "scikit-learn"}
# "use the skill-creator skill"처럼 다른 스킬을 쓰라는 문장
USES_SKILL = re.compile(r"\buse (?:the )?[`'\"]?([\w:-]{3,40})[`'\"]? skill\b|[`'\"]([\w:-]{3,40})[`'\"] 스킬(?:을|로|이)", re.I)
# 저장소 관리자용 절차(빌드·테스트)로 보이는 준비 절. 사용자 준비물로 옮기기 전에 확인한다
# 입출력 형식과 읽기·쓰기 동사가 함께 나온 줄. .hwp를 읽기만 하는지, .hwpx로만 저장하는지 같은 판단 재료다
FORMAT_LINE = re.compile(r"(?=.*\.(?:hwpx?|pptx|potx|docx|xlsx|pdf|html|md|csv|mp4|mov|png|svg)\b)"
                         r"(?=.*\b(?:read[- ]only|output|outputs|save[sd]?|export|generate[sd]?|convert|write|edit|산출|저장|출력|내보|변환|읽기 전용|편집|생성)\b)", re.I)
# 출력 언어를 정하는 지시. 본문 글자 비중은 지시문의 언어일 뿐, 출력 언어는 이런 줄로 정해진다
OUT_LANG = re.compile(r"output language|user'?s (?:preferred )?language|same language as|respond in|reply in|in the user's language"
                      r"|사용자(?:의)? 언어|한국어로|中文|非中文|in Korean|in English", re.I)
DEV_STEPS = re.compile(r"\b(?:pnpm|npm|yarn|bun)\s+(?:run\s+)?(?:build|test|lint|validate|dev)\b|\bmake\s+\w|\bcargo build\b"
                       r"|\bpython3?\s+scripts/", re.I)
TOOLS = {
    "ffmpeg": r"\bff(mpeg|probe)\b",
    "yt-dlp": r"\byt-dlp\b",
    "pandoc": r"\bpandoc\b",
    "LibreOffice": r"\blibreoffice\b|\bsoffice\b",
    "Tesseract OCR": r"\btesseract\b",
    "Poppler": r"\bpoppler\b|\bpdfto(ppm|text|cairo)\b",
    "ImageMagick": r"\bimagemagick\b|\bmagick (convert|identify)\b",
    "Ghostscript": r"\bghostscript\b",
    "Docker": r"\bdocker(-compose| (run|compose|pull|build))\b",
    "Playwright 브라우저": r"\bplaywright install\b",
    "Chrome/Chromium": r"\bchromium\b|\bgoogle-chrome\b|\bChrome (?:browser|브라우저)",
    "Java": r"\bjava -jar\b|\bopenjdk\b",
    "Ollama": r"\bollama\b",
}
INSTALL_CMD = re.compile(
    r"(?:\b(?:sudo\s+)?(?:brew|apt(?:-get)?|dnf|yum|winget|choco|scoop|pipx?3?|pip3|uv tool|uv pip|npm|pnpm|yarn|bun|cargo|go|gem)"
    r"\s+(?:install|add|i|-g)\b[^\n`|;&]*|\buv sync\b[^\n`|;&]*|\bplaywright install\b[^\n`|;&]*)", re.I)
# 로그인은 명령 자리(줄 맨 앞이나 백틱 안)에 있을 때, 또는 "VEED login"처럼 서비스 이름이 붙은 산문일 때만 잡는다
LOGIN = re.compile(r"(?:^[ \t>*-]*(?:\$\s*)?|`)([a-z][\w.-]* (?:auth )?login)\b|\b(gcloud auth|aws configure|claude mcp add|OAuth)\b"
                   r"|\b([A-Z][A-Za-z0-9.]+) (?:login|sign-in)\b", re.M)
NOT_SERVICE = {"The", "Your", "One", "No", "A", "An", "Each", "Same", "User", "Admin", "Root", "This", "That",
               "Any", "New", "Existing", "Free", "Paid", "Service", "Test", "Demo", "My", "Our", "Their", "First", "Single"}
SKILL_DEP = re.compile(r"\bnpx\s+(?:-y\s+|--yes\s+)?skills\s+add\s+(?:https://github\.com/)?([\w.-]+/[\w.-]+)")
MCP_USE = re.compile(r"\bmcp__\w+|\bMCP (?:server|tool)s?\b|\bMCP 서버", re.I)
PAID = re.compile(r"\b(?:paid|pro|enterprise|team|plus)\s+(?:plan|tier|subscription)\b"
                  r"|\b(?:uses?|consumes?|costs?|spends?)\s+(?:[\w-]+\s+){0,3}credits?\b|유료|요금제|크레딧", re.I)
VENV = re.compile(r"\bpython3?\s+-m\s+venv\b|\bvirtualenv\b|source\s+\S*\.?venv", re.I)
# frontmatter의 allowed-tools: Bash(belt *) 같은 줄. 흔한 기본 명령은 준비물이 아니다
ALLOWED_CLI = re.compile(r"Bash\(\s*([\w.-]+)")
COMMON_CLI = {"git", "python", "python3", "node", "npx", "npm", "ls", "cat", "echo", "mkdir", "cp", "mv", "rm",
              "find", "grep", "sed", "awk", "curl", "wget", "bash", "sh", "cd", "pwd", "head", "tail", "jq", "open", "uv", "pip"}
SETUP_DOC = re.compile(r"(^|/)(install|installation|setup|getting[-_]started|prerequisites|requirements)(\.md)?$"
                       r"|(^|/)\.env\.(example|sample|template)$", re.I)
MANIFEST = re.compile(r"(^|/)(requirements[\w.-]*\.txt|pyproject\.toml|package\.json|Pipfile|environment\.ya?ml)$")
# 스텁: SKILL.md가 껍데기이고 실제 지시는 실행할 때 받아 온다. 줄 수가 아니라 표지로 판정한다
# (41줄짜리 K-Skill 스텁을 '40줄 미만' 기준이 놓쳤다)
STUB_MARK = re.compile(r"cli-stub|get the full instructions|\b(?:npx|uvx|bunx|pipx run)\s+[^\n]{0,60}\binstruct\b", re.I)
INSTRUCTION_FILE = re.compile(r"(^|/)(instructions?|INSTRUCTIONS?)\.md$")
DEVISH = re.compile(r"contribut|bug-?hunt|handoff|release|maintain|triage|repo-|dev-|internal|test", re.I)


class Fail(SystemExit):
    pass


def api(path):
    try:
        out = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=30)
        if out.returncode == 0:
            return json.loads(out.stdout)
    except FileNotFoundError:
        pass
    req = urllib.request.Request(f"https://api.github.com/{path}", headers={"Accept": "application/vnd.github+json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        if e.code in (403, 429) and e.headers.get("X-RateLimit-Remaining") == "0":
            raise Fail("GitHub 공개 API 한도(시간당 60회)를 다 썼다. `gh auth login`을 해 두면 시간당 5,000회로 늘어난다."
                       " 사용자에게 알리고, 한도가 풀릴 때까지 이 후보는 '확인 못 함'으로 둔다.")
        raise
    except urllib.error.URLError as e:
        raise Fail(f"GitHub에 닿지 못했다({e.reason}). 네트워크가 막힌 환경(예: Codex 기본 샌드박스)이면"
                   " 네트워크 허용을 요청한다.")


def raw(repo, path, ref):
    """파일 본문을 raw 주소로 받는다. GitHub API의 시간당 한도를 쓰지 않는다."""
    url = f"https://raw.githubusercontent.com/{repo}/{ref}/{urllib.parse.quote(path)}"
    return urllib.request.urlopen(url, timeout=20).read().decode("utf-8", "replace")


def frontmatter(text):
    return text.split("\n---", 1)[0] if text.startswith("---") else ""


def front_desc(text):
    """frontmatter의 description 값. 여러 줄 블록(> 또는 |)도 이어 붙인다."""
    m = re.search(r"^description:[ \t]*(.*)\n((?:[ \t]+.*\n?)*)", text, re.M)
    if not m:
        return ""
    head = m.group(1).strip()
    if head.rstrip("-") in (">", "|", ""):
        head = " ".join(l.strip() for l in m.group(2).splitlines())
    return head.strip("'\" ")


def front_name(text):
    m = re.search(r"^name:\s*['\"]?([^'\"\n]+)", text, re.M)
    return m.group(1).strip() if m else ""


def front_field(text, key):
    m = re.search(rf"^{key}:\s*['\"]?([^'\"\n]+)", frontmatter(text), re.M)
    return m.group(1).strip() if m else ""


def pick_default(repo, skill_mds):
    """스킬 이름 없이 불렸을 때 고를 SKILL.md. 확신할 수 없으면 None.

    1) 저장소 맨 위 SKILL.md. skills CLI도 이름 없이 설치하면 이것만 설치한다.
    2) 폴더 이름이 저장소 이름과 같은 SKILL.md가 하나뿐이면 그것.
    """
    if len(skill_mds) == 1:
        return skill_mds[0]
    if "SKILL.md" in skill_mds:
        return "SKILL.md"
    name = repo.split("/")[-1].lower()
    same = [p for p in skill_mds if posixpath.basename(posixpath.dirname(p)).lower() == name]
    return same[0] if len(same) == 1 else None


def inflated(installs, stars):
    """설치 수에 비해 별이 너무 적으면 경고문을 돌려준다. 복사본이나 부풀린 설치 수를 의심할 신호다."""
    if installs is None or stars is None or installs < INFLATED_MIN or stars * INFLATED_RATIO >= installs:
        return None
    per = f"별 1개당 설치 {installs // stars:,}회" if stars else "별 0개"
    return (f"설치 {installs:,}회에 별 {stars}개({per}). 정상 스킬은 별 1개당 수~수백 회다."
            " 복사본이거나 설치 수가 부풀려졌을 수 있다. 원본 저장소를 찾아 그쪽으로 확인한다")


def registry(repo, skill, known=None):
    """skills.sh에서 이 스킬의 설치 수와, 같은 이름의 스킬이 있는 다른 저장소를 찾는다.
    known(4단계에서 본 설치 수)을 받아도 같은 이름 검사는 한다. 그것이 복사본을 가리는 근거라서다.
    돌려주는 값: (설치 수 또는 None, [(다른 저장소, 설치 수)] 또는 검사하지 못했으면 None, 확인하지 못한 이유 또는 "")."""
    me = f"{repo}/{skill}".lower()
    status, found = search(skill, limit=50)
    if status == "limited":  # 여러 후보를 병렬로 볼 때 흔하다. 서버가 알려 준 시간만큼 한 번 기다렸다 다시 묻는다
        import time
        time.sleep(min(found, 60))
        status, found = search(skill, limit=50)
    if status != "ok":
        return known, None, ("요청 한도" if status == "limited" else f"검색 실패 {found}")
    same = [s for s in found if (s.get("skillId") or s.get("name", "")).lower() == skill.lower()]
    mine = next((s for s in same if s["id"].lower() == me), None)
    if not mine and known is None:  # 상위 50개 밖이면 이 저장소 owner로 좁혀 다시 찾는다
        status, own = search(skill, owner=repo.split("/")[0])
        if status == "ok":
            mine = next((s for s in own if s["id"].lower() == me), None)
    others = sorted(((s.get("source") or s["id"].rsplit("/", 1)[0], s.get("installs") or 0)
                     for s in same if s["id"].lower() != me), key=lambda x: -x[1])
    installs = known if known is not None else (mine.get("installs") if mine else None)
    return installs, others, ("" if installs is not None else "skills.sh에 등록되지 않음")


MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
HTML_ONLY = re.compile(r"^\s*(?:</?[a-zA-Z][^>]*>\s*)+$")


def lines_of(text):
    return text.splitlines()


def in_fence(lines):
    """줄마다 펜스 코드 블록의 언어(블록 밖이면 ""). 코드 안의 플래그(--require 등)를 산문 요구 사항으로 읽지 않고,
    JSX의 import를 Python 패키지로 읽지 않기 위해 쓴다."""
    lang, out = "", []
    for l in lines:
        t = l.strip()
        if t.startswith("```"):
            lang = "" if lang else (t[3:].strip().lower() or "code")
            out.append(lang or "code")
        else:
            out.append(lang)
    return out


def is_optional(lines, i):
    """i번째 줄과 그 위 3줄, 가장 가까운 제목에 선택 표지가 있는가."""
    window = " ".join(lines[max(0, i - 3): i + 1])
    head = next((l for l in reversed(lines[:i + 1]) if l.lstrip().startswith("#")), "")
    return bool(OPTIONAL.search(window) or OPTIONAL.search(head))


def declared_sections(texts, limit_lines=12):
    """본문이 스스로 밝힌 준비 절. [(파일, 시작 줄, 제목, [본문 줄])]. 코드 펜스 안 제목은 무시한다."""
    out = []
    for p, text in texts.items():
        if p.endswith(SCRIPT_EXT) or re.search(r"\.env\.\w+$", p):
            continue
        ls = lines_of(text)
        fence = in_fence(ls)
        i = 0
        while i < len(ls):
            m = re.match(r"^(#{1,4})\s+(.*)", ls[i])
            if m and not fence[i] and PREREQ_HEAD.search(m.group(2)):
                level, body, j = len(m.group(1)), [], i + 1
                while j < len(ls):
                    n = re.match(r"^(#{1,4})\s", ls[j])
                    if n and not fence[j] and len(n.group(1)) <= level:
                        break
                    if ls[j].strip() and not HTML_ONLY.match(ls[j]):
                        body.append(re.sub(r"</?[a-zA-Z][^>]*>", "", MD_LINK.sub(r"\1", ls[j])).rstrip())
                    j += 1
                if body:
                    out.append((p, i + 1, m.group(2).strip(), body[:limit_lines] + (["…"] if len(body) > limit_lines else [])))
                i = j
                continue
            i += 1
    return out


def installed_skill_names():
    """이 컴퓨터에 깔린 스킬 이름(플러그인 접두사를 뗀 것). 못 읽으면 빈 집합."""
    try:
        from find_installed import collect
        return {r[1].split(":")[-1].lower() for r in collect()[0]}
    except Exception:
        return set()


def has_module(mod):
    """이 컴퓨터의 python3에 모듈이 있는가. find_spec은 모듈을 실행하지 않고 위치만 찾는다."""
    import importlib.util
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:
        return False


def prereqs(texts, called, folder_files, repo="", manifests=None, plugin_mcp=None, show=None):
    """설치 명령 하나로 끝나지 않는 준비물의 2차 후보를 모은다.

    texts: {경로: 본문}. called: 스킬이 실제로 부르는 파일 경로 집합(SKILL.md, 설치 문서, SKILL.md가 부르는 스크립트,
    실제 지시 파일). 그 밖의 파일(관리·개발용 스크립트 등)에서만 나온 항목은 따로 모은다.
    show: 경로를 출력용으로 바꾸는 함수(스킬 폴더 기준 상대 경로). 같은 이름의 README가 여러 개여도 가려지게 한다.
    돌려주는 값: {"main": [줄], "other": [줄]}. 각 줄은 '- 종류: 항목 (파일:줄, 선택 표지)' 꼴이다."""
    show = show or (lambda x: x)
    found = {}  # (종류, 항목) -> [(파일:줄, 선택 여부, 부르는 파일인지)]
    versions = {}  # 런타임 -> 본문이 밝힌 버전들
    ver_locs = set()  # 버전을 밝힌 줄. 근거 목록에서 앞에 둔다
    installed = installed_skill_names() if any(USES_SKILL.search(t) for t in texts.values()) else set()

    def add(kind, item, path, ln, optional):
        found.setdefault((kind, item), []).append((f"{show(path)}:{ln}", optional, path in called))

    for p, text in texts.items():
        ls = lines_of(text)
        fence = in_fence(ls)
        script = p.endswith(SCRIPT_EXT)
        envfile = bool(re.search(r"\.env\.\w+$", p))
        env_optional = envfile and bool(OPTIONAL.search(text))
        fm_end = len(lines_of(frontmatter(text))) if p.endswith("SKILL.md") else 0
        for i, l in enumerate(ls):
            opt = env_optional or (not script and is_optional(ls, i))
            if not script:  # 마크다운 링크는 글자만 남긴다. "[Python](url) 3.10+"의 버전을 읽기 위해서다
                l = MD_LINK.sub(r"\1", l)
            if envfile:
                for k in ENV_LINE.findall(l):
                    add("API 키·비밀값", k, p, i + 1, opt)
                continue
            if script:
                for k in ENV_ACCESS.findall(l):
                    add("API 키·비밀값", k, p, i + 1, False)
            elif not NOT_SECRET_LINE.search(l):
                for k in SECRET_VAR.findall(l):
                    add("API 키·비밀값", k, p, i + 1, opt)
            def negated(m):
                """부정어가 같은 구절 안(쉼표·마침표 사이)에 있을 때만 버린다. 줄 전체로 보면
                "COM 불필요, Node.js 18+만 있으면 된다"의 Node.js까지 버리게 된다."""
                if script:
                    return False
                pre = re.split(r"[,.;·，。；、]", l[max(0, m.start() - 40): m.start()])[-1]
                post = re.split(r"[,.;·，。；、]", l[m.end(): m.end() + 20])[0]
                return bool(NEGATED.search(pre) or re.search(r"불필요|필요 없|쓰지 않|not (?:needed|required)", post))
            for label, pat in RUNTIME.items():
                mm = re.search(pat, l, re.I)
                if mm and not negated(mm):
                    v = VERSION.search(l) if label in ("Node.js", "Python") else None
                    if v and not script:
                        versions.setdefault(label, set()).add(v.group(1) or v.group(2))
                        ver_locs.add(f"{show(p)}:{i + 1}")
                    add("런타임", label, p, i + 1, opt)
            for label, pat in TOOLS.items():
                mm = re.search(pat, l, re.I)
                if mm and not negated(mm):
                    add("별도 프로그램", label, p, i + 1, opt)
            if script:
                continue
            if fence[i] in ("python", "py", "python3", "code") and not re.search(r"\bimport\s+[\w{}*, ]+\s+from\s+['\"]", l):
                m = PY_IMPORT.match(l)
                mod = m and (m.group(1) or m.group(2))
                if mod and mod not in STDLIB:
                    here = "이 컴퓨터에 있음" if has_module(mod) else "이 컴퓨터에 없음"
                    pip = PY_PACKAGE.get(mod)
                    label = pip or f"{mod}(import 이름. 설치 이름은 다를 수 있다)"
                    add("Python 패키지(본문 코드의 import)", f"{label}[{here}]", p, i + 1, opt)
            for m in USES_SKILL.finditer(l):
                name = m.group(1) or m.group(2)
                if name and name.lower() not in ("this", "the", "that", "a", "your", "same", "other"):
                    have = name.split(":")[-1].lower() in installed
                    add("함께 쓰는 다른 스킬", f"{name}[{'이 컴퓨터에 설치됨' if have else '설치 안 됨'}]", p, i + 1, opt)
            for m in INSTALL_CMD.finditer(l):
                c = re.sub(r"\s+#.*$", "", re.sub(r"\s+", " ", m.group(0)).strip())  # 줄 끝 주석은 뗀다
                c = re.split(r"[^\x00-\x7f]", c)[0].strip()                         # 뒤에 붙은 한글·중국어 설명은 뗀다
                c = re.sub(r"(?<=\S)[.:,)]+$", "", c)  # 문장 끝 마침표는 떼되 `pip install -e .`의 점은 둔다
                c = re.sub(r"^sudo\s+", "", c)
                if c and not re.search(r"\bskills (add|install)\b|\b(install|add|i|-g)$", c, re.I):  # 인자 없는 명령은 버린다
                    add("추가 설치 명령", c[:70], p, i + 1, opt)
            for m in LOGIN.finditer(l):
                cmd, fixed, service = m.groups()
                if service and service in NOT_SERVICE:
                    continue
                add("계정 로그인·연결", cmd or fixed or f"{service} 계정", p, i + 1, opt)
            for m in SKILL_DEP.finditer(l):
                if m.group(1).lower() != repo.lower():  # 자기 저장소를 설치하는 줄은 선행 스킬이 아니다
                    add("먼저 깔아야 하는 다른 스킬", m.group(1), p, i + 1, opt)
            if MCP_USE.search(l):
                add("MCP 서버", "본문이 MCP 도구·서버를 쓴다", p, i + 1, opt)
            if PAID.search(l) and not fence[i]:
                add("유료 플랜·크레딧", re.sub(r"\s+", " ", l.strip("#>*- ").strip())[:80], p, i + 1, opt)
            if VENV.search(l):
                add("Python 가상환경", "venv 만들기", p, i + 1, opt)
            if p.endswith("SKILL.md") and i < fm_end:
                for c in ALLOWED_CLI.findall(l):
                    if c.lower() not in COMMON_CLI:
                        add("별도 프로그램", c, p, i + 1, False)
                if re.match(r"^\s*mcp(?:Servers)?\s*:", l):
                    add("MCP 서버", "frontmatter에 mcp 설정", p, i + 1, False)

    for m in folder_files:
        if not MANIFEST.search(m):
            continue
        if manifests is not None and m.endswith("package.json") and m not in manifests:
            continue  # 크기 한도로 받지 못한 package.json(대개 node_modules 안)은 뺀다
        dev_only = False
        if m.endswith("package.json") and manifests and m in manifests:
            try:
                pkg = json.loads(manifests[m])
                dev_only = not pkg.get("dependencies") and bool(pkg.get("devDependencies"))
            except Exception:
                pass
        head = "\n".join((manifests or {}).get(m, "").splitlines()[:12])
        opt_head = bool(OPTIONAL.search(head))
        item = posixpath.basename(m) + ("(devDependencies만 있음)" if dev_only else
                                        "(파일 머리에 '선택' 표시. 꼭 필요한 패키지는 주석과 본문에서 확인)" if opt_head else "")
        found.setdefault(("의존성 목록", item), []).append((show(m), dev_only or opt_head, not dev_only))
    for name in plugin_mcp or []:
        found.setdefault(("MCP 서버", f"플러그인이 '{name}' 서버를 함께 설치"), []).append(("plugin.json", False, True))
    for d in folder_files:
        if SETUP_DOC.search(d) and not MANIFEST.search(d) and not re.search(r"README\.md$|\.env\.", d, re.I):
            found.setdefault(("별도 설치 문서", show(d)), []).append((show(d), False, True))

    order = ["런타임", "API 키·비밀값", "별도 프로그램", "MCP 서버", "유료 플랜·크레딧", "계정 로그인·연결",
             "먼저 깔아야 하는 다른 스킬", "함께 쓰는 다른 스킬", "Python 패키지(본문 코드의 import)", "추가 설치 명령",
             "Python 가상환경", "의존성 목록", "별도 설치 문서"]
    main, other = {}, {}
    for (kind, item), where in found.items():
        mine = [w for w in where if w[2]]
        target = main if mine else other
        use = sorted(mine or where, key=lambda w: w[0] not in ver_locs)
        n_opt = sum(1 for w in use if w[1])
        mark = ", 선택 표지" if n_opt == len(use) else (", 일부 줄에 선택 표지" if n_opt else "")
        locs = ", ".join(dict.fromkeys(w[0] for w in use))
        locs = ", ".join(locs.split(", ")[:3]) + (" 외" if len(use) > 3 else "")
        if kind == "런타임" and versions.get(item):
            vs = sorted(versions[item], key=lambda v: [int(x) for x in re.findall(r"\d+", v)])
            item += " " + "/".join(vs) + (" (근거마다 버전이 다르다. 높은 쪽을 적고 엇갈림을 밝힌다)" if len(vs) > 1 else "")
        target.setdefault(kind, []).append(f"{item} ({locs}{mark})")

    def render(d):
        rows = []
        for kind in order:
            if kind in d:
                items = d[kind]
                cap = 6
                rows.append(f"- {kind}: " + "; ".join(items[:cap]) + (f" 외 {len(items) - cap}개" if len(items) > cap else ""))
        return rows

    return {"main": render(main), "other": render(other)}


def language_signal(body):
    """본문 글자 비중과 frontmatter languages. 출력 양식이 어느 언어로 고정됐는지 가늠하는 재료다."""
    text = re.sub(r"```.*?```", "", body, flags=re.S)
    counts = {
        "한국어": len(re.findall(r"[가-힣]", text)),
        "중국어": len(re.findall(r"[一-鿿]", text)),
        "일본어": len(re.findall(r"[぀-ヿ]", text)),
        "영어 등 라틴 문자": len(re.findall(r"[A-Za-z]", text)),
    }
    total = sum(counts.values()) or 1
    share = " · ".join(f"{k} {v * 100 // total}%" for k, v in counts.items() if v * 100 // total >= 1)
    langs = re.search(r"^languages:\s*(.+(?:\n\s+-\s*.+)*)", frontmatter(body), re.M)
    declared = re.sub(r"\s+", " ", langs.group(1)).strip() if langs else ""
    return share + (f" · frontmatter languages: {declared}" if declared else "")


def install_hint(repo, ref, files, path, name, body=""):
    """저장소 구조를 보고 실제로 통하는 설치 명령을 만든다. 추측한 명령을 내지 않기 위해서다.
    돌려주는 값: (설명 줄 목록, 플러그인이 함께 설치하는 MCP 서버 이름 목록)."""
    out, mcp = [], []
    any_standard = any(STANDARD.match(f) for f in files)
    if path:
        deep = not STANDARD.match(path) and any_standard
        if "SKILL.md" in files and path != "SKILL.md":
            deep = True
        cmd = f"npx skills add {repo}" + (f" --skill {name}" if path != "SKILL.md" else "")
        out.append(f"- skills CLI (Claude Code, Codex 등 공용): `{cmd}{' --full-depth' if deep else ''} -g`"
                   + (" (표준 위치에 다른 스킬이 있어 --full-depth 없이는 이 스킬을 못 찾는다)" if deep else ""))
    if ".claude-plugin/marketplace.json" in files:
        try:
            mk = json.loads(raw(repo, ".claude-plugin/marketplace.json", ref))
            # 이 스킬이 들어 있는 플러그인만 고른다. 마켓플레이스 하나에 플러그인이 수십 개일 수 있다.
            for pl in mk.get("plugins", []):
                src = pl.get("source", "")
                if isinstance(src, dict):
                    src = src.get("path", "") if src.get("url", "").rstrip("/").removesuffix(".git").endswith(repo) or "path" in src else ""
                src = str(src).removeprefix("./").strip("/")
                inside = path and (src in ("", ".") or path.startswith(src + "/"))
                listed = [str(x).removeprefix("./").strip("/") for x in pl.get("skills", [])]
                if inside and listed:  # 플러그인이 스킬 목록을 명시하면 그 목록으로 판정한다
                    folder = posixpath.dirname(path)
                    inside = any(folder == posixpath.join(src, x).strip("/") or folder == x for x in listed)
                if inside or (not path and len(mk.get("plugins", [])) == 1):
                    if listed:
                        bundle = [posixpath.basename(x) for x in listed]
                    else:
                        root = "" if src in ("", ".") else src + "/"
                        bundle = [posixpath.basename(posixpath.dirname(f)) or repo.split("/")[1] for f in files
                                  if f.startswith(root) and posixpath.basename(f) == "SKILL.md"
                                  and not VENDORED.search(f[len(root):])]
                    servers = pl.get("mcpServers")
                    cands = [posixpath.join(src, ".claude-plugin/plugin.json").lstrip("/"), posixpath.join(src, ".mcp.json").lstrip("/")]
                    if isinstance(servers, str):  # plugin.json이 별도 파일을 가리키는 경우
                        cands.insert(0, posixpath.normpath(posixpath.join(src, servers)).lstrip("/"))
                        servers = None
                    for mf in cands:
                        if not isinstance(servers, dict) and mf in files:
                            try:
                                d = json.loads(raw(repo, mf, ref))
                                servers = d.get("mcpServers", d if mf.endswith(".json") and "plugin.json" not in mf else None)
                                if isinstance(servers, str):
                                    cands.append(posixpath.normpath(posixpath.join(posixpath.dirname(mf), servers)).lstrip("/"))
                                    servers = None
                            except Exception:
                                pass
                    if isinstance(servers, dict):
                        servers = {k: v for k, v in servers.items() if isinstance(v, dict)}
                    unrelated = ""
                    if servers and body:
                        # 플러그인에 든 MCP 서버가 이 스킬과 상관없을 수 있다(cloudflare/skills의 web-perf는 플러그인의
                        # cloudflare 서버가 아니라 chrome-devtools를 쓴다). 본문이 서버 이름을 부르는 것만 이 스킬의 것으로 본다
                        used = {k: v for k, v in servers.items()  # "chrome-devtools"와 "Chrome DevTools"를 같게 본다
                                if re.search(r"[-_ ]?".join(map(re.escape, re.split(r"[-_ ]+", k))), body, re.I)}
                        if not used:
                            unrelated = (f"- 이 플러그인에는 MCP 서버({', '.join(servers)})가 들어 있지만 이 스킬 본문은 그 이름을 부르지 않는다."
                                       " 스킬이 쓰는 MCP는 '설치 외 준비물'의 MCP 항목과 본문에서 확인한다")
                            unrelated = unrelated
                        servers = used
                    note = ""
                    if len(bundle) > 1:
                        note = (f" (이 플러그인은 스킬 {len(bundle)}개를 함께 설치한다: {', '.join(bundle[:6])}"
                                + (" 외" if len(bundle) > 6 else "") + ")")
                        if len(bundle) >= COLLECTION and not servers:
                            note += ". 묶음이 커서, 이 스킬 하나만 원하면 skills CLI를 먼저 보여 준다"
                    out.append(f"- Claude Code 플러그인 (Claude Code 전용): `/plugin marketplace add {repo}` 다음 "
                               f"`/plugin install {pl['name']}@{mk['name']}`{note}")
                    if unrelated:
                        out.append(unrelated)
                    if servers:
                        mcp = list(servers)
                        # MCP 서버가 본체이면 묶음 크기보다 이것이 앞선다. 서버 없이는 스킬이 작동하지 않을 수 있다
                        out.append(f"- 이 플러그인은 MCP 서버({', '.join(mcp)})를 함께 설치한다. Claude Code 사용자에게는 플러그인을"
                                   " 먼저 보여 준다(묶음이 크면 그 점은 한계에 적는다). skills CLI로 깔면 MCP 서버를 따로 연결한다:")
                        for name_, cfg in list(servers.items())[:3]:
                            if cfg.get("url"):
                                out.append(f"  - Claude Code: `claude mcp add --transport http {name_} {cfg['url']}`"
                                           f" · Codex: `codex mcp add {name_} --url {cfg['url']}`")
                            elif cfg.get("command"):
                                cmd = " ".join([cfg["command"], *map(str, cfg.get("args", []))])
                                env = " (환경 변수 필요: " + ", ".join(cfg["env"]) + ")" if cfg.get("env") else ""
                                out.append(f"  - Claude Code: `claude mcp add {name_} -- {cmd}` · Codex: `codex mcp add {name_} -- {cmd}`{env}")
                    break
        except Exception:
            out.append("- Claude Code 플러그인 마켓플레이스 파일이 있다(.claude-plugin/marketplace.json)")
    if not out and not path:
        return ["- 스킬을 고른 뒤 owner/repo@skill로 다시 부르면 그 스킬의 설치 명령이 나온다"], mcp
    return (out or ["- 설치 경로를 확정하지 못했다. `npx skills add <repo> --list --full-depth`로 확인한다"]), mcp


# skills CLI가 기본으로 뒤지는 "컨테이너" 폴더. 루트, skills/(와 .curated 등), data/skills, agent/skills,
# 그리고 에이전트별 숨김 폴더(.claude/skills, .agents/skills, .posit/assistant/skills 등)다. 컨테이너 안은
# 세 단계(skills/<이름>, skills/<분류>/<이름>, skills/<분류>/<분류>/<이름>)까지 내려간다.
# 출처: vercel-labs/skills README "Skill Discovery" (2026-10 확인)
# 컨테이너에 스킬이 하나라도 있으면 CLI는 거기서 멈추고, 하나도 없을 때만 저장소 전체를 뒤진다.
# 그래서 컨테이너에 다른 스킬이 있는 저장소에서 컨테이너 밖의 스킬을 설치하려면 --full-depth가 필요하다.
# (chrisryugj/kordoc에서 확인: .claude/skills/gongmunseo가 있어 plugins/kordoc/skills/kordoc를 못 찾음)
CONTAINER = (r"(skills|skills/\.(curated|experimental|system)|data/skills|agent/skills"
             r"|\.[\w-]+/skills|\.[\w-]+/[\w-]+/skills)")
STANDARD = re.compile(rf"^(SKILL\.md|{CONTAINER}/([^/]+/){{1,3}}SKILL\.md)$")


def fetch_many(repo, ref, paths, workers=12):
    def one(p):
        try:
            return p, raw(repo, p, ref)
        except Exception:
            return p, None
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        return dict(ex.map(one, paths))


def list_skills(repo, ref, skill_mds, why):
    """어느 스킬인지 정하지 못했을 때, 목록을 설명과 함께 보여 준다. 폴더 이름만으로 고르지 않게 하기 위해서다."""
    print(f"\n# {why}. 아래에서 고른 뒤 owner/repo@skill로 다시 부른다. 실패가 아니다.")
    bodies = fetch_many(repo, ref, skill_mds[:60])
    print(f"# 저장소 안 스킬 {len(skill_mds)}개: 폴더 | name | description")
    for p in skill_mds[:60]:
        b = bodies.get(p) or ""
        d = front_desc(b)
        marks = []
        if VENDORED.search(p) and DEVISH.search(p):
            marks.append("저장소 개발·관리용으로 보임")
        if re.search(r"\bcargo build\b|\bgit clone\b|\bmake\s+(?:build|install)\b", b):
            marks.append("직접 빌드·복제 필요")
        if re.search(r"\]\(\.\./|`\.\./", b):
            marks.append("스킬 폴더 밖 참조")
        dev = f" [{'; '.join(marks)}]" if marks else ""
        print(f"- {posixpath.dirname(p) or '(맨 위)'} | {front_name(b) or '?'} | {d[:120]}{'…' if len(d) > 120 else ''}{dev}")
    if len(skill_mds) > 60:
        print(f"- 외 {len(skill_mds) - 60}개")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="owner/repo@skill 또는 owner/repo")
    ap.add_argument("--lines", type=int, default=300, help="SKILL.md 본문(과 실제 지시 파일) 출력 줄 수 상한")
    ap.add_argument("--installs", type=int, help="4단계에서 본 skills.sh 설치 수. 넘기면 설치 수 조회만 건너뛴다")
    ap.add_argument("--show", action="append", default=[], metavar="파일:줄[-줄]",
                    help="근거 줄을 열어 본다. 출력에 나온 경로 그대로 쓴다(예: 루트/README.md:192, scripts/x.py:10-30). 여러 번 쓸 수 있다")
    a = ap.parse_args()
    if not TARGET.match(a.target):
        sys.exit(f"대상 형식이 틀렸다: '{a.target}'. owner/repo 또는 owner/repo@skill 하나만 넘긴다"
                 " (옵션은 따로 띄어 쓴다).")

    repo, _, skill = a.target.partition("@")
    try:
        meta = api(f"repos/{repo}")
    except Fail:
        raise
    except Exception as e:
        sys.exit(f"저장소를 읽지 못했다: {repo} ({e}). 이름이 바뀌었거나 비공개·삭제된 저장소다. 추천 대상에서 뺀다.")
    repo = meta.get("full_name", repo)
    ref = meta["default_branch"]
    pushed = meta.get("pushed_at", "")[:10]
    stale = pushed and (dt.date.today() - dt.date.fromisoformat(pushed)).days > 365
    stars = meta.get("stargazers_count")

    say = print if not a.show else (lambda *x, **k: None)  # --show는 근거 줄만 낸다
    say(f"# 저장소: https://github.com/{repo}")
    say(f"- 별: {stars} · 포크: {meta.get('forks_count')} · 만든 날: {meta.get('created_at', '')[:10]}"
          f" · 크기: 약 {max(1, (meta.get('size') or 0) // 1024)}MB")
    say(f"- 최근 push: {pushed}{' (1년 넘게 갱신 없음)' if stale else ''} · archived: {meta.get('archived')}")
    if meta.get("fork"):
        say(f"- 이 저장소는 포크다. 원본: https://github.com/{(meta.get('parent') or {}).get('full_name', '?')}")
    lic = (meta.get("license") or {}).get("spdx_id")
    say(f"- 설명: {meta.get('description') or ''}")

    tree = api(f"repos/{repo}/git/trees/{ref}?recursive=1")
    blobs = [t for t in tree.get("tree", []) if t["type"] == "blob"]
    files = [t["path"] for t in blobs]
    sizes = {t["path"]: t.get("size", 0) for t in blobs}
    if tree.get("truncated"):
        print("- 주의: 저장소가 너무 커서 파일 목록이 잘렸다. 스킬 목록과 설치 판정이 불완전할 수 있다")
    skill_mds = [p for p in files if posixpath.basename(p) == "SKILL.md"]
    readme_path = next((p for p in files if p.lower() == "readme.md"), None)
    readme = ""
    if readme_path:
        try:
            readme = raw(repo, readme_path, ref)
        except Exception:
            pass
    moved = [(i + 1, l.strip()[:140]) for i, l in enumerate(readme.splitlines()[:60]) if MOVED.search(l)][:3]

    if not skill_mds:
        print("\n# 저장소에 SKILL.md가 없다. 스킬이 아니거나 구조가 다르거나 다른 곳으로 옮겼다.")
        if moved:
            print("# README의 이전·폐기 표시:")
            print("\n".join(f"- README.md:{n} {t}" for n, t in moved))
        if readme:
            print("# README 앞부분 (옮긴 곳이 적혀 있으면 그 저장소로 다시 부른다):")
            print("\n".join(readme.splitlines()[:20]))
        sys.exit(0)

    path, picked = None, ""
    if skill:
        path = next((p for p in skill_mds if posixpath.basename(posixpath.dirname(p)) == skill), None)
        if not path:  # 폴더 이름과 스킬 이름이 다른 경우 frontmatter로 찾는다(raw로 받아 API 한도를 쓰지 않는다)
            bodies = fetch_many(repo, ref, skill_mds[:80])
            path = next((p for p in skill_mds[:80] if front_name(bodies.get(p) or "") == skill), None)
    else:
        path = pick_default(repo, skill_mds)
        if path and len(skill_mds) > 1:
            why = ("저장소 맨 위 SKILL.md다. skills CLI도 스킬 이름 없이 설치하면 이것만 설치한다" if path == "SKILL.md"
                   else "폴더 이름이 저장소 이름과 같다")
            others = [q for q in skill_mds if q != path]
            picked = (f"- 저장소에 스킬이 {len(skill_mds)}개라 이것을 기본으로 골랐다({why})."
                      f" 다른 스킬: {', '.join(posixpath.dirname(q) for q in others[:8])}"
                      + (" 외" if len(others) > 8 else "") + ". 그쪽이 맞으면 owner/repo@skill로 다시 부른다")
    if not path:
        list_skills(repo, ref, skill_mds, f"'{skill}'에 맞는 SKILL.md를 못 찾았다" if skill else "저장소에 스킬이 여러 개다")
        print("\n# 설치 방법")
        print("\n".join(install_hint(repo, ref, files, None, None)[0]))
        sys.exit(0)

    body = raw(repo, path, ref)
    folder = posixpath.dirname(path)
    # 스킬 폴더 안의 파일. 그 안에 다른 스킬 폴더가 들어 있으면(맨 위 스킬이 흔히 그렇다) 그쪽은 뺀다
    nested = [posixpath.dirname(q) + "/" for q in skill_mds if q != path and (folder == "" or q.startswith(folder + "/"))]
    siblings = [p for p in files if (folder == "" or p.startswith(folder + "/"))
                and not any(p.startswith(n) for n in nested)]
    name = front_name(body) or skill or posixpath.basename(folder) or repo.split("/")[-1]
    rel = lambda p: p[len(folder) + 1:] if folder and p.startswith(folder + "/") else p

    if a.show:  # 근거 줄 열어 보기. 손으로 gh api를 부르지 않게 하기 위해서다
        for spec in a.show:
            m = re.match(r"^(.+?):(\d+)(?:-(\d+))?$", spec)
            if not m:
                print(f"# 형식이 틀렸다: {spec} (파일:줄 또는 파일:시작-끝)")
                continue
            f, lo = m.group(1), int(m.group(2))
            hi = int(m.group(3)) if m.group(3) else lo + 4
            lo = max(1, lo - (0 if m.group(3) else 4))
            # 출력의 경로는 스킬 폴더 기준이고 '루트/'가 붙은 것만 저장소 맨 위 기준이다. 같은 기준으로 찾는다
            root_only = spec.startswith("루트/") or m.group(1).startswith("루트/")
            f = re.sub(r"^루트/", "", f)
            order = (f,) if root_only or not folder else (f"{folder}/{f}", f)
            target = next((c for c in order if c in files), None)
            if not target:
                print(f"# 파일을 찾지 못했다: {f}")
                continue
            try:
                ls = (body if target == path else raw(repo, target, ref)).splitlines()
            except Exception as e:
                print(f"# 읽지 못했다: {target} ({e})")
                continue
            print(f"# {target} {lo}-{min(hi, len(ls))}줄")
            print("\n".join(f"{i:>5}| {ls[i - 1]}" for i in range(lo, min(hi, len(ls)) + 1)))
        return

    # 스텁 판정과 실제 지시 파일
    lines = body.splitlines()
    stub = bool(STUB_MARK.search(body)) or bool(len(lines) < 40 and re.search(r"\b(npx|uvx|pipx|curl|wget)\b", body))
    instr_paths = [p for p in siblings if INSTRUCTION_FILE.search(p)]  # 스킬 폴더의 지시 파일은 스텁이 아니어도 함께 본다
    if stub and not instr_paths:
        instr_paths = [p for p in files if INSTRUCTION_FILE.search(p) and name.lower() in p.lower()][:1]

    scripts = [p for p in siblings if p.endswith(SCRIPT_EXT)]
    bundled = [p for p in scripts if BUNDLED.search(p)]
    # SKILL.md가 이름을 부르는 스크립트(실제로 실행되는 것)를 먼저, 그다음 얕은 위치부터
    own = sorted((p for p in scripts if not BUNDLED.search(p)),
                 key=lambda p: (posixpath.basename(p) not in body,
                                bool(re.search(r"(^|/)tests?/|test_", p)),  # 테스트는 실행되지 않으니 뒤로
                                p.count("/"), p))
    targets = [p for p in own if sizes.get(p, 0) <= MAX_BYTES][:MAX_SCAN]
    unscanned = [p for p in own if p not in targets]
    setup_docs = [p for p in siblings if SETUP_DOC.search(p) and sizes.get(p, 0) <= MAX_BYTES][:6]
    folder_readme = next((p for p in siblings if p.lower() == (folder + "/readme.md" if folder else "readme.md")), None)
    if folder_readme and folder_readme not in setup_docs:  # 스킬 폴더 맨 위 README만. scripts/README 같은 하위 README는 관리용이 많다
        setup_docs.append(folder_readme)
    manifest_paths = [p for p in siblings if MANIFEST.search(p) and sizes.get(p, 0) <= MAX_BYTES][:5]

    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        reg = ex.submit(registry, repo, name, a.installs)
        docs = {p: t for p, t in fetch_many(repo, ref, setup_docs + instr_paths[:2]).items() if t is not None}
        manifests = {p: t for p, t in fetch_many(repo, ref, manifest_paths).items() if t is not None}
        fetched = fetch_many(repo, ref, targets)
        installs, same_name, unknown = reg.result()
    scan = {path: body}
    for p in targets:
        text = fetched.get(p)
        if text is None:
            unscanned.append(p)
        elif max((len(l) for l in text.splitlines()), default=0) > 3000:  # 압축된 빌드 결과물
            bundled.append(p)
        else:
            scan[p] = text
    scan.update(docs)
    instr = {p: docs[p] for p in instr_paths if p in docs}

    # 스킬이 실제로 부르는 파일: SKILL.md, 설치 문서, 실제 지시 파일, 그리고 SKILL.md(나 지시 파일)가 이름을 부르는 스크립트
    said = body + "".join(instr.values())
    called = {path, *docs} | {p for p in scan if p.endswith(SCRIPT_EXT)
                              and (posixpath.basename(p) in said or rel(p) in said)}

    hits = {}
    for p, text in scan.items():
        for pat, why in RISK:
            m = re.search(pat, text, re.I)
            if m:
                line = text.count("\n", 0, m.start()) + 1
                hits.setdefault(why, []).append(f"{rel(p)}:{line} `{m.group(0)[:60]}`")
    for p, text in [(path, body), *instr.items()]:  # 스킬 본문이 다른 스킬·플러그인 설치를 직접 지시하는가
        for m in re.finditer(r"\bnpx\s+(?:-y\s+|--yes\s+)?skills\s+add\s+(?:https://github\.com/)?([\w.-]+/[\w.-]+)([^\n`]*)|/plugin install \S+", text):
            line = text.count("\n", 0, m.start()) + 1
            if not m.group(1) or m.group(1).lower() != repo.lower():
                hits.setdefault("스킬이 다른 스킬·플러그인 설치를 직접 지시", []).append(f"{rel(p)}:{line} `{m.group(0)[:60]}`")
                continue
            # 같은 저장소라도 다른 스킬을 깔라는 지시면 잡는다(next-bundle-optimizer가 next-dev-loop 설치를 지시)
            tail = m.group(2) or ""
            other = re.search(r"--skill\s+([\w.-]+)|/skills/([\w.-]+)", tail)
            target = other and (other.group(1) or other.group(2))
            if target and target.lower() != name.lower():
                where = f"{rel(p)}:{line} → {target}"
                lst = hits.setdefault("스킬이 같은 저장소의 다른 스킬 설치를 직접 지시", [])
                if where not in lst:
                    lst.append(where)
    signals = []
    for why, where in hits.items():  # 같은 종류는 3곳까지만 보여 주고 나머지는 개수로
        more = f" 외 {len(where) - 3}곳" if len(where) > 3 else ""
        signals.append(f"- {why} ({len(where)}곳): " + "; ".join(where[:3]) + more)
    if stub:
        signals.append("- 스텁: SKILL.md가 껍데기이고 실제 지시는 실행할 때 받아 온다. 지금 읽은 지시와 설치 뒤 실행되는 지시가"
                       " 다를 수 있다" + (f". 저장소 사본: {', '.join(instr_paths[:2])} (아래에 출력)" if instr_paths else
                                          ". 저장소에서 지시 파일을 찾지 못했다"))

    # 라이브러리 카드 여부
    try:
        from find_library import repo_index, is_self
        cards = repo_index().get(repo.lower(), [])
    except Exception:
        cards, is_self = [], (lambda r: False)

    print(f"\n# 스킬: {name} ({path})")
    if picked:
        print(picked)
    if cards:
        c = cards[0]
        print(f"- AI Roasting 라이브러리 카드: {c['name']} (카테고리 {c['category']}"
              + (", 에디터픽" if c.get("editors_pick") else "") + ")"
              + (". AI Roasting 자체 제작이다. 추천할 때 큐레이터의 자기 스킬임을 밝힌다" if is_self(repo) else ""))
    own_kept = [p for p in own if p not in bundled]
    folder_mb = sum(sizes.get(p, 0) for p in siblings) / 1_048_576
    print(f"- 스킬 폴더 크기 약 {folder_mb:.1f}MB, 파일 {len(siblings)}개, 실행 스크립트 {len(scripts)}개"
          f" (저자 작성 {len(own_kept)}개, 함께 든 라이브러리·빌드 결과물 {len(bundled)}개는 검사 제외)")
    if own_kept:
        shown = list(dict.fromkeys(rel(p) for p in own_kept))
        print(f"- 저자 스크립트: {', '.join(shown[:10])}" + (f" 외 {len(shown) - 10}개" if len(shown) > 10 else ""))
    print(f"- 라이선스: {lic if lic and lic != 'NOASSERTION' else front_field(body, 'license') or '감지 안 됨'}")

    print("\n# 설치 방법 (저장소 구조로 확인한 명령. 이 줄을 그대로 쓴다)")
    hint, plugin_mcp = install_hint(repo, ref, files, path, name, body + "\n".join(instr.values()))
    print("\n".join(hint))
    if (meta.get("size") or 0) > 500_000:
        print(f"- 저장소가 커서(약 {meta['size'] // 1024}MB) skills CLI가 내려받는 데 오래 걸릴 수 있다. 한계에 적는다")
    outside = sorted({x for t in re.findall(r"\]\((\.\./[^)\s]+)\)|`(\.\./[^`\s]+)`", body) for x in t if x})
    if outside:
        print(f"- 스킬 폴더 밖을 참조한다: {', '.join(outside[:3])}. skills CLI로 이 스킬만 깔면 참조가 끊긴다."
              " 플러그인이나 저장소 단위 설치가 필요할 수 있다")

    show = lambda p: rel(p) if (folder == "" or p.startswith(folder + "/")) else f"루트/{p}"
    print("\n# 설치 외 준비물")
    print("## 1차 근거: 본문이 밝힌 준비 (원문. SKILL.md·설치 문서 절이 우선이다. README 절은 저장소 관리용일 수 있다)")
    texts = {path: body, **docs}
    # 맨 위 README는 저장소가 사실상 이 스킬 하나일 때(스킬 3개 이하)만 이 스킬의 문서로 본다
    if readme and readme_path not in texts and (folder == "" or len(skill_mds) <= 3):
        texts[readme_path] = readme
        called.add(readme_path)
    sections = declared_sections(texts)
    fm_all = frontmatter(body).splitlines()
    fm_lines = []
    for i, l in enumerate(fm_all):  # 키와 그 아래 들여 쓴 값(mcp:\n  server: office-mcp 등)을 함께 본다
        if FM_KEYS.match(l):
            kids = []
            for k in fm_all[i + 1:]:
                if not k.startswith((" ", "\t")):
                    break
                kids.append(k.strip())
            fm_lines.append(l.strip() + (" " + " ".join(kids[:6]) if kids else ""))
    if fm_lines:
        print("- SKILL.md frontmatter: " + " / ".join(l.strip() for l in fm_lines))
    for p, ln, title, blk in sections[:4]:
        dev = " [빌드·테스트 같은 저장소 관리 절차로 보인다. 사용자 준비물로 옮기지 않는다]" if DEV_STEPS.search("\n".join(blk)) else ""
        print(f"- {show(p)}:{ln} \"{title}\"{dev}")
        print("\n".join(f"    {l[:160]}" for l in blk))
    if not sections and not fm_lines:
        print("- 본문에 준비·설치·요구 사항 절이 없다")
    print("## 2차 후보: 패턴으로 찾은 것 (파일:줄을 열어 확인한 것만 옮긴다. '선택 표지'는 근처에 optional·선택 같은 말이 있다는 뜻)")
    texts_all = {**texts, **{p: t for p, t in scan.items() if p.endswith(SCRIPT_EXT)}}
    found = prereqs(texts_all, called, siblings, repo, manifests, plugin_mcp, show)
    print("\n".join(found["main"]) if found["main"] else "- 스킬이 부르는 파일에서는 걸린 것 없음")
    if found["other"]:
        print("## 스킬이 부르지 않는 파일에서만 나온 것 (관리·개발용이거나 선택 기능일 수 있다. README의 설명을 확인한다)")
        print("\n".join(found["other"]))
    # 근거로 든 줄이 아래 본문 출력 범위 밖이면 그 줄을 여기서 보여 준다(다시 부르지 않아도 되게)
    beyond = sorted({int(n) for n in re.findall(r"(?<![\w/])SKILL\.md:(\d+)", "\n".join(found["main"])) if int(n) > a.lines})
    if beyond:
        print(f"## 본문 출력 범위({a.lines}줄) 밖에 있는 근거 줄")
        for n in beyond[:10]:
            print(f"  {n:>4}| {lines[n - 1][:200] if n <= len(lines) else ''}")
    fmt_lines = [(i + 1, l.strip()) for i, l in enumerate(lines) if FORMAT_LINE.search(l) and not l.lstrip().startswith("#")][:6]
    if fmt_lines:
        print("## 형식 신호 (입출력 형식과 읽기·쓰기를 가늠할 줄. 1단계의 산출 형식과 맞는지 본다)")
        print("\n".join(f"  {n:>4}| {t[:180]}" for n, t in fmt_lines))

    print("\n# 발동·언어")
    dmi = re.search(r"^disable-model-invocation:\s*true", frontmatter(body), re.M | re.I)
    desc = front_desc(body)
    print("- 자동 발동: " + ("꺼짐(disable-model-invocation: true). 사용자가 /이름으로 직접 불러야 한다" if dmi
                            else "description이 비었거나 깨졌다. 자동으로 발동하지 않을 수 있다" if len(desc) < 10
                            else f"켜짐 (description {len(desc)}자)"))
    print(f"- 지시문 언어 비중: {language_signal(body + chr(10).join(instr.values()))}"
          + (" (실제 지시 파일 포함)" if instr else "") + ". 지시문의 언어일 뿐 출력 언어가 아니다")
    said_lines = [(i + 1, l.strip()) for i, l in enumerate(lines) if OUT_LANG.search(l)][:4]
    print("- 출력 언어 지시: " + ("; ".join(f"SKILL.md:{n} {t[:120]}" for n, t in said_lines) if said_lines
                                 else "본문에 없다. 템플릿 제목·예시가 어느 언어로 고정됐는지 본문에서 확인한다"))

    print("\n# 신뢰 신호 (5단계 '믿을 만한가'에 쓴다)")
    print(f"- skills.sh 설치 수: {f'{installs:,}' if installs is not None else f'미확인({unknown})'} · 별: {stars}")
    checked = same_name is not None
    same_name = same_name or []
    trust = []
    if stale:
        trust.append(f"- 1년 넘게 갱신 없음(최근 push {pushed})")
    if meta.get("archived"):
        trust.append("- archived 저장소다. 더는 고쳐지지 않는다")
    if meta.get("fork"):
        trust.append("- 포크 저장소다. 원본 저장소를 먼저 본다")
    for n, t in moved:
        trust.append(f"- 이전·폐기 표시: README.md:{n} {t}")
    for i, l in enumerate(lines[:30]):
        if MOVED.search(l):
            trust.append(f"- 이전·폐기 표시: SKILL.md:{i + 1} {l.strip()[:140]}")
            break
    if VENDORED.search(path):
        where = path.split('/skills/')[0] + "/skills/"
        if same_name:
            trust.append(f"- 설치본 경로({where})에 있다. 이 저장소가 원본이 아니라 다른 곳의 스킬을 가져다 둔 사본일 수 있다."
                         " 같은 이름의 스킬 목록에서 원본을 찾는다")
        else:  # 다른 곳에 같은 이름이 없으면 저장소 자체 스킬일 가능성이 크다(rhwp-safe-edit에서 확인)
            trust.append(f"- 참고: 설치본 경로({where})에 있지만 skills.sh에 같은 이름의 스킬이 다른 곳에 없다."
                         " 저장소가 자기 작업용으로 둔 스킬일 가능성이 크다")
    if len(skill_mds) >= COLLECTION:
        trust.append(f"- 저장소에 스킬이 {len(skill_mds)}개다. 별은 모음 전체에 붙은 수라 이 스킬 하나의 인기로 읽지 않는다")
    if warn := inflated(installs, stars):
        trust.append(f"- 복사본 의심: {warn}")
    if not same_name:
        trust.append("- 같은 이름 검사: " + (f"하지 못했다({unknown}). 1분 뒤 다시 부르면 한다" if not checked
                                         else "skills.sh 상위 50개 안에 같은 이름의 다른 저장소가 없다"))
    if same_name:
        owner = repo.split("/")[0].lower()
        listed = ", ".join(f"{r}({n:,}{', 같은 owner' if r.split('/')[0].lower() == owner else ''})" for r, n in same_name[:6]) \
            + (" 외" if len(same_name) > 6 else "")
        top = (installs is not None and installs > same_name[0][1] and not inflated(installs, stars)
               and not VENDORED.search(path))
        if top:  # 설치본 경로도 아니고 설치 수 1위면 원본일 가능성이 크다. 목록은 참고로만 짧게 낸다
            trust.append(f"- 참고: 같은 이름의 스킬이 다른 저장소 {len(same_name)}곳에 있으나, 이 저장소가 설치 수 1위다"
                         f"(다음: {same_name[0][0]} {same_name[0][1]:,})")
        else:
            trust.append(f"- 같은 이름의 스킬이 다른 저장소 {len(same_name)}곳에 있다(skills.sh 상위 50개 기준): {listed}. 이 저장소가 원본인지"
                         " 별, 만든 날, 경로로 가린다. 원본 후보는 find_inspect.py로 다시 확인한다")
    print("\n".join(trust) if trust else "- 걸린 것 없음")

    print("\n# 위험 신호 (직접 읽고 판단할 곳)")
    print("\n".join(signals) if signals else "- 패턴 검사에서 걸린 것 없음")
    print(f"- 검사 범위: SKILL.md, 설치·지시 문서 {len(docs)}개, 저자 스크립트 {len([p for p in scan if p.endswith(SCRIPT_EXT)])}개")
    if unscanned:
        print(f"- 검사하지 못한 저자 스크립트 {len(unscanned)}개(한도 초과·큰 파일): "
              + ", ".join(rel(p) for p in unscanned[:8]) + (" 외" if len(unscanned) > 8 else "")
              + ". 위험이 중요한 후보면 진입 스크립트를 직접 읽는다")

    for p, text in instr.items():
        il = text.splitlines()
        print(f"\n# 실제 지시 파일: {p} ({len(il)}줄" + (f", 앞 {a.lines}줄만 표시" if len(il) > a.lines else "")
              + "). 실행할 때 받아 오는 지시의 저장소 사본이다. 기능·한계는 여기서 확인한다")
        print("\n".join(f"{i + 1:>4}| {l}" for i, l in enumerate(il[: a.lines])))

    print(f"\n# SKILL.md 본문 ({len(lines)}줄" + (f", 앞 {a.lines}줄만 표시. 나머지는 --lines로 본다" if len(lines) > a.lines else "")
          + "). 줄 앞 숫자는 줄 번호다. 다른 파일의 특정 줄은 --show 파일:줄로 본다")
    print("\n".join(f"{i + 1:>4}| {l}" for i, l in enumerate(lines[: a.lines])))


if __name__ == "__main__":
    main()
