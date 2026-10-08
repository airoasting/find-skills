#!/usr/bin/env python3
"""find-skills 4단계: skills.sh 검색을 여러 키워드로 한 번에 돌리고 결과를 합친다.

`npx skills find`는 터미널 색상 코드가 섞인 출력을 내고, 한 번에 한 질의만 받는다.
이 스크립트는 질의들을 병렬로 돌려 색상 코드를 걷어내고, 같은 스킬을 하나로 합쳐
설치 수 순으로 출력한다.

사용법:
  python3 scripts/find_search.py "meeting notes" "transcript summary"
  python3 scripts/find_search.py "pdf" --owner anthropics --owner openai
  python3 scripts/find_search.py "hwp" --exclude-repo airoasting/find-skills

출력 열: 설치 수 | owner/repo@skill | 걸린 질의 | skills.sh 링크
"""
import argparse
import concurrent.futures as cf
import re
import subprocess
import time

ANSI = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")
HIT = re.compile(r"^([\w.-]+/[\w.-]+)@(\S+)\s+([\d.]+)([KM]?)\s+installs?", re.I)
URL = re.compile(r"(https://skills\.sh/\S+)")


def installs(num, unit):
    return int(float(num) * {"": 1, "K": 1_000, "M": 1_000_000}[unit.upper()])


def run(query, owner, timeout, retry=True):
    cmd = ["npx", "--yes", "skills", "find", query]
    if owner:
        cmd += ["--owner", owner]
    label = f"{query}" + (f" (owner:{owner})" if owner else "")
    try:
        out = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True,
                             text=True, timeout=timeout).stdout
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
    except FileNotFoundError:
        raise SystemExit("npx가 없다. Node.js가 필요하다. https://skills.sh/ 를 웹으로 읽어 대신한다.")
    lines = [ANSI.sub("", l).strip() for l in out.splitlines()]
    hits = []
    for i, line in enumerate(lines):
        m = HIT.match(line)
        if not m:
            continue
        url = ""
        if i + 1 < len(lines) and (u := URL.search(lines[i + 1])):
            url = u.group(1)
        hits.append((f"{m.group(1)}@{m.group(2)}", installs(m.group(3), m.group(4)), url))
    # skills.sh는 분당 요청 수를 넘기면 오류 대신 "No skills found"를 돌려준다.
    # 빈 결과를 곧이곧대로 믿지 않고 한 번 쉬었다가 다시 묻는다.
    if not hits and retry:
        time.sleep(30)
        label, hits = run(query, owner, timeout, retry=False)
        return label, hits
    return label, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("queries", nargs="+", help="영문 검색어. 여러 개를 주면 병렬로 돌린다")
    ap.add_argument("--owner", action="append", default=[],
                    help="공식 출처를 따로 볼 때. 각 질의를 이 owner로 한 번 더 검색한다")
    ap.add_argument("--exclude-repo", action="append", default=[],
                    help="이미 고른 저장소(owner/repo)를 결과에서 뺀다")
    ap.add_argument("--min-installs", type=int, default=0)
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--timeout", type=int, default=90)
    a = ap.parse_args()

    jobs = [(q, None) for q in a.queries] + [(q, o) for q in a.queries for o in a.owner]
    merged = {}
    with cf.ThreadPoolExecutor(max_workers=min(6, len(jobs))) as ex:
        for label, hits in ex.map(lambda j: run(*j, a.timeout), jobs):
            if not hits:
                print(f"# 결과 없음(30초 뒤 재시도까지 함): {label}")
            for key, n, url in hits:
                e = merged.setdefault(key, {"n": n, "url": url, "q": []})
                e["n"] = max(e["n"], n)
                e["url"] = e["url"] or url
                if label not in e["q"]:
                    e["q"].append(label)

    excl = {r.lower() for r in a.exclude_repo}
    rows = [(v["n"], k, v) for k, v in merged.items()
            if k.split("@")[0].lower() not in excl and v["n"] >= a.min_installs]
    rows.sort(reverse=True)
    if not merged:
        print("# 모든 질의가 비었다. 요청 제한(분당 약 30회)일 수 있다. 1분 뒤 한 번만 다시 돌리고,"
              " 그래도 비면 https://skills.sh/ 를 웹으로 확인한다.")
    print(f"# 후보 {len(rows)}개 (상위 {min(len(rows), a.limit)}개 표시)")
    for n, key, v in rows[: a.limit]:
        print(f"{n:>9,} | {key} | {', '.join(v['q'])} | {v['url']}")


if __name__ == "__main__":
    main()
