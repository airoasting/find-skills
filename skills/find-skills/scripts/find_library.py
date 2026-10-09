#!/usr/bin/env python3
"""find-skills 3단계: AI Roasting 스킬 라이브러리를 매칭용 압축 목록으로 출력한다.

skills.json(약 100KB)을 통째로 읽지 않고, 매칭에 필요한 필드만 한 줄씩 뽑는다.
순위는 매기지 않는다. 어떤 카드가 맞는지는 이 출력을 읽은 에이전트가 판단한다.

사용법:
  python3 scripts/find_library.py                       # 전체
  python3 scripts/find_library.py --cat korea           # 카테고리 한정
  python3 scripts/find_library.py --grep "hwp|한글"      # 이름·태그·설명에 이 말이 든 카드만(정규식)
  python3 scripts/find_library.py --pick                # 에디터픽만
  python3 scripts/find_library.py --full                # 설명 두 문장 모두 (기본은 첫 문장만)

--grep은 순위가 아니라 회수 보조다. 맞는 카테고리가 분명하지 않을 때 150장을 눈으로 훑는 대신 쓴다.
걸리지 않은 카드가 맞을 수도 있으니, 걸린 카드의 카테고리는 --cat으로 한 번 더 본다.

출력의 SELF 표시는 AI Roasting이 직접 만든 스킬이다. 큐레이터 자신의 스킬이므로 추천할 때 밝힌다.
"""
import argparse
import json
import os
import pathlib
import re
import sys
import tempfile
import time
import urllib.request

URL = "https://skill.airoasting.com/skills.json"
SELF_OWNERS = {"airoasting"}  # 라이브러리 운영자. 이 owner의 카드는 자체 제작이다
CACHE = pathlib.Path(tempfile.gettempdir()) / "find-skills-library.json"
CACHE_TTL = 3600
# 카탈로그 저장소(airoasting/find-skills) 안에서 돌 때만 있는 로컬 사본: skills/find-skills/scripts → 저장소 루트
_HERE = pathlib.Path(__file__).resolve()
LOCAL = _HERE.parents[3] / "docs" / "skills.json" if len(_HERE.parents) > 3 else _HERE.parent / "skills.json"


def load(source=None):
    """(데이터, 출처 설명). 라이브 사이트를 1시간 캐시하고, 닿지 않으면 로컬 사본을 쓴다.
    find_search.py와 find_inspect.py도 라이브러리 저장소 표시에 이 함수를 쓴다."""
    if source:
        if source.startswith("http"):
            return json.load(urllib.request.urlopen(source, timeout=20)), source
        return json.loads(pathlib.Path(source).read_text()), source
    try:
        if CACHE.exists() and time.time() - CACHE.stat().st_mtime < CACHE_TTL:
            return json.loads(CACHE.read_text()), f"{URL} (캐시)"
    except Exception:
        pass
    try:
        data = json.load(urllib.request.urlopen(URL, timeout=20))
        try:
            CACHE.write_text(json.dumps(data, ensure_ascii=False))
        except Exception:
            pass
        return data, URL
    except Exception as e:  # 네트워크가 막히면 로컬 사본으로
        if LOCAL.exists():
            return json.loads(LOCAL.read_text()), f"{LOCAL} (원격 실패: {e})"
        raise RuntimeError(f"라이브러리를 읽지 못했다: {e}")


def repo_index():
    """{owner/repo 소문자: [카드, ...]}. 라이브러리를 읽지 못하면 빈 사전."""
    try:
        data, _ = load()
    except Exception:
        return {}
    idx = {}
    for s in data.get("skills", []):
        idx.setdefault(s["repo"].lower().strip("/"), []).append(s)
    return idx


def is_self(repo):
    return repo.split("/")[0].lower() in SELF_OWNERS


def first_sentence(text):
    # 카드 설명은 "무엇인지. 누구에게 왜 맞는지." 두 문장이다. 매칭에는 첫 문장이면 충분하다.
    m = re.match(r"(.+?(?:니다|다|요)\.)\s", text + " ")
    return m.group(1) if m else text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cat", action="append", default=[],
                    help="카테고리 id로 한정. 여러 번 쓰거나 쉼표로 이어도 된다(--cat design,writing)")
    ap.add_argument("--grep", help="이름·저장소·태그·설명에 이 정규식이 든 카드만 (대소문자 무시)")
    ap.add_argument("--pick", action="store_true", help="editors_pick만")
    ap.add_argument("--full", action="store_true", help="설명 두 문장을 모두 출력")
    ap.add_argument("--source", help="skills.json 경로나 URL (기본: 라이브 사이트)")
    a = ap.parse_args()

    try:
        data, src = load(a.source)
    except Exception as e:
        sys.exit(f"{e}. 네트워크가 막힌 환경(예: Codex 기본 샌드박스)이면 네트워크 허용을 요청한다."
                 " 그래도 안 되면 3단계를 건너뛰고 '검색 범위' 줄에 그렇게 적는다.")
    cats = {c["id"]: c for c in data["categories"]}
    wanted = {c.strip() for x in a.cat for c in x.split(",") if c.strip()}
    bad = wanted - set(cats)
    if bad:
        sys.exit(f"없는 카테고리 id: {', '.join(sorted(bad))}. 가능한 값: {', '.join(cats)}")
    pat = re.compile(a.grep, re.I) if a.grep else None

    total = len(data["skills"])
    skills = [
        s for s in data["skills"]
        if (not wanted or s["category"] in wanted) and (not a.pick or s.get("editors_pick"))
        and (not pat or pat.search(" ".join([s["name"], s["repo"], " ".join(s.get("tags", [])), s.get("desc", "")])))
    ]

    print(f"# source: {src}")
    if not wanted:  # 카테고리로 좁혔으면 표를 다시 찍지 않는다
        print("# categories: id | 이름 | 무엇을 위한 카테고리인가")
        for c in data["categories"]:
            print(f"{c['id']} | {c['name']} | {c.get('desc', '')}")
    scope = " · ".join(x for x in [wanted and f"cat={','.join(sorted(wanted))}", a.grep and f"grep={a.grep}", a.pick and "pick"] if x)
    print(f"\n# 라이브러리 전체 {total}개" + (f", 이 출력 {len(skills)}개 ({scope})" if scope else "")
          + ". '검색 범위' 줄에는 전체 수와 어떻게 좁혔는지를 쓴다")
    print(f"# skills ({len(skills)}): category | name | repo | stars | pick | tags | desc   (SELF = AI Roasting 자체 제작)")
    for s in skills:
        mark = "PICK" if s.get("editors_pick") else "-"
        if is_self(s["repo"]):
            mark += " SELF"
        tags = " ".join(s.get("tags", []))
        desc = s.get("desc", "") if a.full else first_sentence(s.get("desc", ""))
        print(f"{s['category']} | {s['name']} | {s['repo']} | ★{s.get('stars', '?')} | {mark} | {tags} | {desc}")
    if pat and skills:
        hit = sorted({s["category"] for s in skills})
        print(f"\n# --grep은 회수 보조다. 걸린 카드의 카테고리({', '.join(hit)})를 --cat으로 한 번 더 훑으면 놓친 카드를 줄인다")


if __name__ == "__main__":
    main()
