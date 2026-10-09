#!/usr/bin/env python3
"""find-skills 릴리스 점검. pre-commit 훅이 커밋 직전에 부른다.

스킬 파일(SKILL.md, scripts/find_*.py, .claude-plugin/)을 고쳤는데 plugin.json의 version을 그대로 두면,
플러그인으로 설치한 사람은 `claude plugin update`를 해도 새 버전을 받지 못한다.
플러그인 갱신이 버전 번호로 판단되기 때문이다. 그래서 그런 커밋을 막는다.

막지 않고 넘기려면(오타 수정처럼 배포가 필요 없는 변경): SKIP_RELEASE_CHECK=1 git commit ...
"""
import json
import os
import re
import subprocess
import sys

MANIFEST = ".claude-plugin/plugin.json"
# 스킬로 설치되어 동작하는 파일. 카탈로그 운영용 스크립트(sync-*.py, check_release.py)와 docs/는 배포 대상이 아니다
SKILL_FILE = re.compile(r"^(SKILL\.md|\.claude-plugin/.+|scripts/find_\w+\.py)$")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout


def version_at(ref):
    text = git("show", f"{ref}:{MANIFEST}")
    return json.loads(text)["version"] if text.strip() else None


def main():
    if os.environ.get("SKIP_RELEASE_CHECK") == "1":
        return 0
    staged = [p for p in git("diff", "--cached", "--name-only").splitlines() if SKILL_FILE.match(p)]
    if not staged:
        return 0

    new = json.loads(open(MANIFEST).read())
    errors = []

    # SKILL.md의 name과 플러그인 이름이 어긋나면 설치 후 스킬 이름이 달라진다
    body = open("SKILL.md").read()
    m = re.search(r"^name:\s*(\S+)", body, re.M)
    if not m or m.group(1) != new["name"]:
        errors.append(f"SKILL.md name({m.group(1) if m else '없음'})과 plugin.json name({new['name']})이 다르다")

    old = version_at("HEAD")
    content_changed = [p for p in staged if p != MANIFEST]
    if content_changed and old is not None and old == new["version"]:
        errors.append(
            f"스킬 파일 {len(content_changed)}개를 고쳤는데 version이 {old} 그대로다. "
            f"{MANIFEST}의 version을 올린다(작은 수정 1.1.0→1.1.1, 기능 추가 1.1.0→1.2.0)."
        )

    if errors:
        print("find-skills 릴리스 점검 실패:")
        print("\n".join(f"  - {e}" for e in errors))
        print("  배포가 필요 없는 변경이면 SKIP_RELEASE_CHECK=1 git commit ... 으로 넘긴다.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
