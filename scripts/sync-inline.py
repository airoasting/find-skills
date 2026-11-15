#!/usr/bin/env python3
"""skills.json → index.html 의 <script id="skills-data"> 블록 자동 동기화.

단일 소스: skills.json
로컬(file://)에서도 데이터가 바로 보이도록 인라인 백업 제공.
커밋 직전 .githooks/pre-commit 이 호출.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "docs" / "index.html"
JSON = ROOT / "docs" / "skills.json"
MCP_HTML = ROOT / "docs" / "mcp" / "index.html"


def bake_text(text, key, count, cats):
    text = re.sub(r'(<[a-z]+[^<>]*data-count="%s"[^<>]*>)[^<]*(<)' % key, lambda m: m.group(1) + str(count) + m.group(2), text)
    return re.sub(r'(<[a-z]+[^<>]*data-cats="%s"[^<>]*>)[^<]*(<)' % key, lambda m: m.group(1) + cats + m.group(2), text)


def bake(path, key, count, cats):
    """다른 페이지의 첫 화면에 보이는 개수(data-count)와 분야 줄(data-cats)을 HTML에 써 넣는다.
    각 페이지는 자기 숫자만 실행 중에 계산하므로, 상대편 숫자는 여기서 맞춘다."""
    if not path.exists():
        return False
    old = path.read_text(encoding="utf-8")
    new = re.sub(r'(<[a-z]+[^<>]*data-count="%s"[^<>]*>)[^<]*(<)' % key, lambda m: m.group(1) + str(count) + m.group(2), old)
    new = re.sub(r'(<[a-z]+[^<>]*data-cats="%s"[^<>]*>)[^<]*(<)' % key, lambda m: m.group(1) + cats + m.group(2), new)
    if new == old:
        return False
    path.write_text(new, encoding="utf-8")
    try:
        subprocess.run(["git", "add", str(path)], cwd=ROOT, check=False)
    except Exception:
        pass
    return True


def main() -> int:
    if not HTML.exists() or not JSON.exists():
        print("sync-inline: index.html 또는 skills.json 을 찾을 수 없습니다.", file=sys.stderr)
        return 1

    html = HTML.read_text(encoding="utf-8")
    skills = JSON.read_text(encoding="utf-8").strip()

    new_block = (
        '<script type="application/json" id="skills-data">\n'
        f"{skills}\n"
        "</script>"
    )

    pattern = re.compile(
        r'<script[^>]*id="skills-data"[^>]*>.*?</script>',
        re.DOTALL,
    )

    if pattern.search(html):
        new_html = pattern.sub(lambda _m: new_block, html, count=1)
    else:
        # </body> 직전에 삽입
        new_html = re.sub(r'(\s*)</body>', r'\n' + new_block + r'\1</body>', html, count=1)

    # MCP 허브 첫 화면에 보이는 스킬 개수와 분야 줄
    data = json.loads(skills)
    cats = " · ".join(c.get("short", c["name"]) for c in data.get("categories", []))
    if bake(MCP_HTML, "skills", len(data.get("skills", [])), cats):
        print("sync-inline: mcp/index.html 의 스킬 개수·분야 갱신")
    new_html = bake_text(new_html, "skills", len(data.get("skills", [])), cats)

    if new_html == html:
        return 0

    HTML.write_text(new_html, encoding="utf-8")
    # 스테이징 (pre-commit 에서 호출될 때)
    try:
        subprocess.run(["git", "add", str(HTML)], cwd=ROOT, check=False)
    except Exception:
        pass
    print("sync-inline: index.html 인라인 skills-data 동기화 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
