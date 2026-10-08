#!/usr/bin/env python3
"""find-skills 3단계: AI Roasting 스킬 라이브러리를 매칭용 압축 목록으로 출력한다.

skills.json(약 100KB)을 통째로 읽지 않고, 매칭에 필요한 필드만 한 줄씩 뽑는다.
순위는 매기지 않는다. 어떤 카드가 맞는지는 이 출력을 읽은 에이전트가 판단한다.

사용법:
  python3 scripts/find_library.py                 # 전체
  python3 scripts/find_library.py --cat korea     # 카테고리 한정
  python3 scripts/find_library.py --pick          # 에디터픽만
  python3 scripts/find_library.py --full          # 설명 두 문장 모두 (기본은 첫 문장만)
"""
import argparse
import json
import pathlib
import sys
import re
import urllib.request

URL = "https://skill.airoasting.com/skills.json"
# 카탈로그 저장소(airoasting/find-skills) 안에서 돌 때만 있는 로컬 사본: skills/find-skills/scripts → 저장소 루트
_HERE = pathlib.Path(__file__).resolve()
LOCAL = _HERE.parents[3] / "docs" / "skills.json" if len(_HERE.parents) > 3 else _HERE.parent / "skills.json"


def load(source):
    if source:
        if source.startswith("http"):
            return json.load(urllib.request.urlopen(source, timeout=20)), source
        return json.loads(pathlib.Path(source).read_text()), source
    try:
        return json.load(urllib.request.urlopen(URL, timeout=20)), URL
    except Exception as e:  # 네트워크가 막히면 로컬 사본으로
        if LOCAL.exists():
            return json.loads(LOCAL.read_text()), f"{LOCAL} (원격 실패: {e})"
        sys.exit(f"라이브러리를 읽지 못했다: {e}. 3단계를 건너뛰고 4단계로 간다.")


def first_sentence(text):
    # 카드 설명은 "무엇인지. 누구에게 왜 맞는지." 두 문장이다. 매칭에는 첫 문장이면 충분하다.
    m = re.match(r"(.+?(?:니다|다|요)\.)\s", text + " ")
    return m.group(1) if m else text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cat", help="카테고리 id로 한정")
    ap.add_argument("--pick", action="store_true", help="editors_pick만")
    ap.add_argument("--full", action="store_true", help="설명 두 문장을 모두 출력")
    ap.add_argument("--source", help="skills.json 경로나 URL (기본: 라이브 사이트)")
    a = ap.parse_args()

    data, src = load(a.source)
    cats = {c["id"]: c for c in data["categories"]}
    if a.cat and a.cat not in cats:
        sys.exit(f"없는 카테고리 id: {a.cat}. 가능한 값: {', '.join(cats)}")

    skills = [
        s for s in data["skills"]
        if (not a.cat or s["category"] == a.cat) and (not a.pick or s.get("editors_pick"))
    ]

    print(f"# source: {src}")
    print("# categories: id | 이름 | 무엇을 위한 카테고리인가")
    for c in data["categories"]:
        print(f"{c['id']} | {c['name']} | {c.get('desc', '')}")
    print(f"\n# skills ({len(skills)}): category | name | repo | stars | pick | tags | desc")
    for s in skills:
        pick = "PICK" if s.get("editors_pick") else "-"
        tags = " ".join(s.get("tags", []))
        desc = s.get("desc", "") if a.full else first_sentence(s.get("desc", ""))
        print(f"{s['category']} | {s['name']} | {s['repo']} | ★{s.get('stars', '?')} | {pick} | {tags} | {desc}")


if __name__ == "__main__":
    main()
