#!/usr/bin/env python3
"""find-skills 5단계: 후보 스킬 하나를 저장소 전체를 내려받지 않고 검증한다.

저장소 메타(별, 최근 push, archived, 라이선스)를 읽고, 저장소 안에서 해당 스킬의
SKILL.md를 찾아 본문을 출력한다. 같은 폴더의 스크립트 파일에서 위험 신호
(원격 스크립트 실행, 자격 증명 접근 등)를 찾아 표시한다. 신호는 판정이 아니라
읽을 곳을 가리키는 표시다. 최종 판단은 본문을 읽은 에이전트가 한다.

사용법:
  python3 scripts/find_inspect.py anthropics/skills@pdf
  python3 scripts/find_inspect.py owner/repo@skill --lines 200

gh CLI가 로그인돼 있으면 그것을 쓰고, 아니면 GitHub 공개 API(시간당 60회)를 쓴다.
"""
import argparse
import base64
import concurrent.futures as cf
import datetime as dt
import json
import posixpath
import re
import subprocess
import sys
import urllib.parse
import urllib.request

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
]
SCRIPT_EXT = (".sh", ".py", ".js", ".ts", ".mjs", ".cjs", ".rb", ".ps1")
# 저자가 쓴 코드가 아니라 함께 들어 있는 라이브러리·빌드 결과물. 압축된 한 줄짜리 코드라 패턴 검사가
# 오탐(React의 dangerouslySetInnerHTML, 브라우저의 atob 등)만 내고, 검사 한도를 먼저 채워 저자의
# 스크립트를 밀어낸다. 그래서 검사에서 빼고 개수만 알린다.
BUNDLED = re.compile(r"(^|/)(vendor|vendors|dist|build|node_modules|third_party)/"
                     r"|[.-]min\.(js|css)$|\.(umd|bundle|chunk)\.js$")
MAX_SCAN = 200         # 검사할 저자 스크립트 수 상한. raw 주소로 받아 API 한도를 쓰지 않는다
MAX_BYTES = 200_000    # 이보다 큰 파일은 사람이 쓴 스크립트가 아닐 가능성이 크다


def api(path):
    try:
        out = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=30)
        if out.returncode == 0:
            return json.loads(out.stdout)
    except FileNotFoundError:
        pass
    req = urllib.request.Request(f"https://api.github.com/{path}",
                                 headers={"Accept": "application/vnd.github+json"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def content(repo, path, ref):
    d = api(f"repos/{repo}/contents/{path}?ref={ref}")
    return base64.b64decode(d["content"]).decode("utf-8", "replace")


def raw(repo, path, ref):
    """파일 본문을 raw 주소로 받는다. GitHub API의 시간당 한도를 쓰지 않아 많이 받아도 된다."""
    url = f"https://raw.githubusercontent.com/{repo}/{ref}/{urllib.parse.quote(path)}"
    return urllib.request.urlopen(url, timeout=20).read().decode("utf-8", "replace")


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


def install_hint(repo, ref, files, path, name):
    """저장소 구조를 보고 실제로 통하는 설치 명령을 만든다. 추측한 명령을 내지 않기 위해서다."""
    out = []
    any_standard = any(STANDARD.match(f) for f in files)
    if path:
        deep = not STANDARD.match(path) and any_standard
        if "SKILL.md" in files and path != "SKILL.md":
            deep = True
        cmd = f"npx skills add {repo}" + (f" --skill {name}" if path != "SKILL.md" else "")
        out.append(f"- skills CLI: `{cmd}{' --full-depth' if deep else ''} -g`"
                   + (" (표준 위치에 다른 스킬이 있어 --full-depth 없이는 이 스킬을 못 찾는다)" if deep else ""))
    if ".claude-plugin/marketplace.json" in files:
        try:
            mk = json.loads(content(repo, ".claude-plugin/marketplace.json", ref))
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
                    out.append(f"- Claude Code 플러그인: `/plugin marketplace add {repo}` 다음 "
                               f"`/plugin install {pl['name']}@{mk['name']}`")
                    break
        except Exception:
            out.append("- Claude Code 플러그인 마켓플레이스 파일이 있다(.claude-plugin/marketplace.json)")
    return out or ["- 설치 경로를 확정하지 못했다. `npx skills add <repo> --list --full-depth`로 확인한다"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="owner/repo@skill 또는 owner/repo")
    ap.add_argument("--lines", type=int, default=300, help="SKILL.md 본문 출력 줄 수 상한")
    a = ap.parse_args()

    repo, _, skill = a.target.partition("@")
    try:
        meta = api(f"repos/{repo}")
    except Exception as e:
        sys.exit(f"저장소를 읽지 못했다: {repo} ({e})")
    ref = meta["default_branch"]
    pushed = meta.get("pushed_at", "")[:10]
    stale = ""
    if pushed:
        days = (dt.date.today() - dt.date.fromisoformat(pushed)).days
        stale = " (1년 넘게 갱신 없음)" if days > 365 else ""

    print(f"# 저장소: https://github.com/{repo}")
    print(f"- 별: {meta.get('stargazers_count')} · 포크: {meta.get('forks_count')}")
    print(f"- 최근 push: {pushed}{stale} · archived: {meta.get('archived')}")
    lic = (meta.get("license") or {}).get("spdx_id")
    print(f"- 라이선스: {lic if lic and lic != 'NOASSERTION' else '저장소 루트에서 감지 안 됨(SKILL.md나 하위 폴더에 있을 수 있다)'}")
    print(f"- 설명: {meta.get('description') or ''}")

    tree = api(f"repos/{repo}/git/trees/{ref}?recursive=1")
    blobs = [t for t in tree.get("tree", []) if t["type"] == "blob"]
    files = [t["path"] for t in blobs]
    sizes = {t["path"]: t.get("size", 0) for t in blobs}
    skill_mds = [p for p in files if posixpath.basename(p) == "SKILL.md"]
    if not skill_mds:
        sys.exit("\n저장소에 SKILL.md가 없다. 스킬이 아니거나 구조가 다르다. 추천 대상에서 뺀다.")

    path = None
    if skill:
        path = next((p for p in skill_mds if posixpath.basename(posixpath.dirname(p)) == skill), None)
        if not path:  # 폴더 이름과 스킬 이름이 다른 경우 frontmatter로 찾는다
            for p in skill_mds[:40]:
                if front_name(content(repo, p, ref)) == skill:
                    path = p
                    break
    elif len(skill_mds) == 1:
        path = skill_mds[0]
    if not path:
        why = f"'{skill}'에 맞는 SKILL.md를 못 찾았다" if skill else "저장소에 스킬이 여러 개다"
        print(f"\n# {why}. owner/repo@skill 형식으로 다시 부른다.")
        print("# 저장소 안 SKILL.md 목록 (폴더 이름이 대개 스킬 이름이다):")
        print("\n".join(f"- {p}" for p in skill_mds[:50]))
        print("\n# 설치 방법")
        print("\n".join(install_hint(repo, ref, files, None, None)))
        sys.exit(1)

    body = content(repo, path, ref)
    folder = posixpath.dirname(path)
    siblings = [p for p in files if folder == "" or p.startswith(folder + "/")]
    scripts = [p for p in siblings if p.endswith(SCRIPT_EXT)]

    bundled = [p for p in scripts if BUNDLED.search(p)]
    # SKILL.md가 이름을 부르는 스크립트(실제로 실행되는 것)를 먼저, 그다음 얕은 위치부터
    own = sorted((p for p in scripts if not BUNDLED.search(p)),
                 key=lambda p: (posixpath.basename(p) not in body,
                                bool(re.search(r"(^|/)tests?/|test_", p)),  # 테스트는 실행되지 않으니 뒤로
                                p.count("/"), p))
    targets = [p for p in own if sizes.get(p, 0) <= MAX_BYTES][:MAX_SCAN]
    unscanned = [p for p in own if p not in targets]

    def fetch(p):
        try:
            return p, raw(repo, p, ref)
        except Exception:
            return p, None

    scan = {path: body}
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        for p, text in ex.map(fetch, targets):
            if text is None:
                unscanned.append(p)
            elif max((len(l) for l in text.splitlines()), default=0) > 3000:  # 압축된 빌드 결과물
                bundled.append(p)
            else:
                scan[p] = text
    hits = {}
    for p, text in scan.items():
        for pat, why in RISK:
            m = re.search(pat, text, re.I)
            if m:
                line = text.count("\n", 0, m.start()) + 1
                hits.setdefault(why, []).append(f"{p}:{line} `{m.group(0)[:60]}`")
    signals = []
    for why, where in hits.items():  # 같은 종류는 3곳까지만 보여 주고 나머지는 개수로
        more = f" 외 {len(where) - 3}곳" if len(where) > 3 else ""
        signals.append(f"- {why} ({len(where)}곳): " + "; ".join(where[:3]) + more)
    lines = body.splitlines()
    # 본문이 짧고 외부 도구를 부르면, 실제 지시는 실행할 때 받아 오는 스텁일 수 있다.
    # 그러면 지금 읽은 본문과 설치 뒤 실행되는 지시가 다를 수 있다.
    if len(lines) < 40 and re.search(r"\b(npx|uvx|pipx|curl|wget)\b", body):
        signals.append("- 스텁 가능성: 본문이 짧고 외부 도구를 부른다. 실제 지시가 실행 시점에 바뀔 수 있다")
    if len(front_desc(body)) < 10:
        signals.append("- description이 비었거나 깨졌다: 자동 발동이 안 될 수 있다")

    print(f"\n# 스킬: {front_name(body) or skill} ({path})")
    own_kept = [p for p in own if p not in bundled]
    print(f"- 스킬 폴더 파일 {len(siblings)}개, 실행 스크립트 {len(scripts)}개"
          f" (저자 작성 {len(own_kept)}개, 함께 든 라이브러리·빌드 결과물 {len(bundled)}개는 검사 제외)")
    if own_kept:
        print(f"- 저자 스크립트: {', '.join(posixpath.basename(p) for p in own_kept[:10])}"
              + (" 외" if len(own_kept) > 10 else ""))
    print("\n# 설치 방법 (저장소 구조로 확인한 명령. 이 줄을 그대로 쓴다)")
    print("\n".join(install_hint(repo, ref, files, path, front_name(body) or skill)))
    print("\n# 위험 신호 (직접 읽고 판단할 곳)")
    print("\n".join(signals) if signals else "- 패턴 검사에서 걸린 것 없음")
    print(f"- 검사 범위: SKILL.md와 저자 스크립트 {len(scan) - 1}개")
    if unscanned:
        print(f"- 검사하지 못한 저자 스크립트 {len(unscanned)}개(한도 초과·큰 파일): "
              + ", ".join(unscanned[:8]) + (" 외" if len(unscanned) > 8 else "")
              + ". 위험이 중요한 후보면 진입 스크립트를 직접 읽는다")

    print(f"\n# SKILL.md 본문 ({len(lines)}줄" + (f", 앞 {a.lines}줄만 표시" if len(lines) > a.lines else "") + ")")
    print("\n".join(lines[: a.lines]))


if __name__ == "__main__":
    main()
