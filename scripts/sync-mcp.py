#!/usr/bin/env python3
"""docs/mcp/index.html 의 DATA 배열 → docs/mcp.json.

MCP 허브의 정본은 docs/mcp/index.html 안의 DATA 배열이다(화면이 그 배열을 그대로 그린다).
find-skills의 find_library.py가 MCP 커넥터도 찾을 수 있도록, 같은 내용을 기계가 읽는 JSON으로 내보낸다.
mcp.json은 손으로 고치지 않는다. 카드를 바꾸면 DATA 배열을 고치고 이 스크립트를 돌린다.
커밋 직전 .githooks/pre-commit 이 호출한다.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "docs" / "mcp" / "index.html"
OUT = ROOT / "docs" / "mcp.json"
AUTH = {"none": "바로 사용", "login": "로그인만 필요", "api": "API 발급 필요"}
ROW = re.compile(r'^\s*(\[".*\]),\s*$')  # DATA 배열의 한 줄. 줄 자체가 JSON 배열이다


def main() -> int:
    if not HTML.exists():
        print(f"sync-mcp: {HTML} 을 찾을 수 없습니다.", file=sys.stderr)
        return 1
    text = HTML.read_text(encoding="utf-8")
    start, end = text.find("const DATA = ["), text.find("const CATS = [")
    if start < 0 or end < 0:
        print("sync-mcp: DATA 배열을 찾지 못했습니다.", file=sys.stderr)
        return 1
    cats = json.loads(re.search(r"const CATS = (\[.*?\]);", text).group(1))
    rows = []
    for line in text[start:end].splitlines():
        m = ROW.match(line)
        if not m:
            continue
        name, _mono, category, source, stars, forks, desc, repo, auth = json.loads(m.group(1))
        rows.append({
            "name": name, "category": category, "source": source,
            "repo": "/".join(repo.split("/")[:2]),  # k-skill 계열은 저장소 안 폴더 경로가 붙어 있다
            "url": "https://github.com/" + repo,
            "stars": stars, "forks": forks, "desc": desc,
            "auth": auth, "auth_label": AUTH[auth],
        })
    if not rows:
        print("sync-mcp: 카드를 한 장도 읽지 못했습니다.", file=sys.stderr)
        return 1
    data = {"site": "https://skill.airoasting.com/mcp/", "categories": cats, "connectors": rows}
    new = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if OUT.exists() and OUT.read_text(encoding="utf-8") == new:
        return 0
    OUT.write_text(new, encoding="utf-8")
    try:
        subprocess.run(["git", "add", str(OUT)], cwd=ROOT, check=False)
    except Exception:
        pass
    print(f"sync-mcp: mcp.json 갱신 ({len(rows)}건)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
