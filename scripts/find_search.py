#!/usr/bin/env python3
"""find-skills 4단계: skills.sh 검색을 여러 키워드로 한 번에 돌리고 결과를 합친다.

`npx skills find`가 부르는 검색 API(https://skills.sh/api/search)를 직접 부른다. CLI를 거치면
요청 한도 초과(HTTP 429)와 진짜 빈 결과가 똑같이 "No skills found"로 나와 둘을 가를 수 없고,
설치 수도 "705.2K"처럼 반올림된다. API를 직접 부르면 둘 다 정확하다.

출력을 정하는 원칙:
  - 정렬은 '걸린 질의 수'가 먼저, 설치 수가 다음이다. 여러 질의에 함께 걸린 스킬이 의도에 가깝고,
    설치 수 순으로만 줄 세우면 질의와 먼 인기 스킬(예: Lark 75만)이 위를 차지한다.
  - 기본으로 모든 줄을 보인다. 상위 몇 줄만 보이면 맞는 후보가 아래에 묻힌다(실제로 54번째에 있었다).
  - 줄마다 스킬 설명을 붙인다(skills.sh 스킬 페이지에서 읽는다. 이 페이지는 요청 한도가 없다).
    이름만 보고 거르지 않게 하기 위해서다.
  - 같은 이름의 스킬이 이 검색 결과 안에 2곳 이상이면 한 줄로 접고, 나머지 저장소를 함께 적는다.
  - AI Roasting 라이브러리에 있는 저장소는 [라이브러리: 카드 이름]으로 표시한다.
  - 검색 결과는 10분, 설명은 하루 캐시한다. --limit만 바꿔 다시 볼 때 요청 한도를 쓰지 않는다.

사용법:
  python3 scripts/find_search.py "meeting notes" "transcript summary"
  python3 scripts/find_search.py "pdf" --owner anthropics --owner openai      # --owner는 여러 번 쓸 수 있다
  python3 scripts/find_search.py "hwp" --exclude chrisryugj/kordoc@kordoc      # 저장소 또는 저장소@스킬

출력 열: 설치 수 | owner/repo@skill | 걸린 질의 | 설명 | 표시 | skills.sh 링크
"""
import argparse
import concurrent.futures as cf
import hashlib
import html
import json
import os
import pathlib
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True  # 설치된 스킬 폴더에 __pycache__를 남기지 않는다
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE = os.environ.get("SKILLS_API_URL", "https://skills.sh").rstrip("/")
API = BASE + "/api/search"
PAGE = os.environ.get("SKILLS_PAGE_URL", "https://www.skills.sh").rstrip("/")
PER_QUERY = 20      # skills CLI와 같은 값
RATE_LIMIT = 30     # skills.sh 검색 API 분당 요청 한도 (429 응답 본문에 명시, 2026-10 확인)
CACHE_DIR = pathlib.Path(tempfile.gettempdir()) / "find-skills-cache"
SEARCH_TTL = 600
DESC_TTL = 86400


def _cache(kind, key, ttl, value=None):
    """캐시 읽기(value 없음) 또는 쓰기. 캐시는 편의일 뿐이라 실패해도 조용히 넘어간다."""
    path = CACHE_DIR / f"{kind}-{hashlib.sha1(key.encode()).hexdigest()[:16]}.json"
    try:
        if value is None:
            if path.exists() and time.time() - path.stat().st_mtime < ttl:
                return json.loads(path.read_text())
            return None
        CACHE_DIR.mkdir(exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False))
    except Exception:
        return None


def search(query, owner=None, limit=PER_QUERY, timeout=60):
    """("ok", skills) | ("limited", 기다릴 초) | ("error", 메시지)."""
    params = {"q": query, "limit": str(limit)}
    if owner:
        params["owner"] = owner
    key = json.dumps([API, params], sort_keys=True)
    hit = _cache("search", key, SEARCH_TTL)
    if hit is not None:
        return "ok", hit
    req = urllib.request.Request(f"{API}?{urllib.parse.urlencode(params)}", headers={"User-Agent": "find-skills"})
    try:
        skills = json.load(urllib.request.urlopen(req, timeout=timeout)).get("skills", [])
        _cache("search", key, SEARCH_TTL, skills)
        return "ok", skills
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return "limited", int(e.headers.get("Retry-After") or 60)
        return "error", f"HTTP {e.code}"
    except Exception as e:
        return "error", str(e)


def describe(skill_id, timeout=15):
    """skills.sh 스킬 페이지의 meta description. 페이지 앞 12KB만 읽는다. 못 읽으면 ""."""
    hit = _cache("desc", skill_id, DESC_TTL)
    if hit is not None:
        return hit
    try:
        req = urllib.request.Request(f"{PAGE}/{skill_id}", headers={"User-Agent": "find-skills"})
        head = urllib.request.urlopen(req, timeout=timeout).read(12_000).decode("utf-8", "replace")
        m = re.search(r'<meta name="description" content="([^"]*)"', head)
        desc = html.unescape(m.group(1)).strip() if m else ""
        if desc.startswith("Discover and install skills"):  # 스킬 페이지가 아니라 사이트 기본 설명
            desc = ""
        _cache("desc", skill_id, DESC_TTL, desc)
        return desc
    except Exception:
        return ""


def base_query(label):
    return label.split(" (owner:")[0]


def collapse(rows, library=()):
    """같은 스킬 이름이 2곳 이상이면 한 줄로 접는다. rows는 이미 정렬된 상태다.
    묶음 안에 AI Roasting 라이브러리 저장소가 있으면 그 줄을 대표로 세운다. 큐레이션을 거친 원본이
    설치 23회짜리 사본 뒤에 숨는 일을 막기 위해서다(HWPX Skill에서 확인).
    rows: [(installs, "owner/repo@skill", info)]. library: 라이브러리 저장소(소문자) 집합.
    돌려주는 값: [(대표 줄, [접힌 줄...])]. 대표는 묶음에서 가장 앞선 줄의 자리에 놓인다."""
    by_name = {}
    for r in rows:
        by_name.setdefault(r[1].split("@", 1)[1].lower(), []).append(r)
    out = []
    for r in rows:
        group = by_name[r[1].split("@", 1)[1].lower()]
        if len(group) < 2:
            out.append((r, []))
        elif r is group[0]:
            lead = next((g for g in group if g[1].split("@")[0].lower() in library), group[0])
            out.append((lead, [g for g in group if g is not lead]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("queries", nargs="+", help="영문 검색어. 여러 개를 주면 병렬로 돌린다")
    ap.add_argument("--owner", action="append", default=[],
                    help="공식 출처를 따로 볼 때. 여러 번 쓸 수 있다. 각 질의를 이 owner로 한 번 더 검색한다")
    ap.add_argument("--exclude", "--exclude-repo", action="append", default=[], dest="exclude",
                    help="이미 고른 후보를 뺀다. owner/repo@skill이면 그 스킬만, owner/repo면 저장소 전체. 여러 번 쓸 수 있다")
    ap.add_argument("--min-installs", type=int, default=0)
    ap.add_argument("--per-query", type=int, default=PER_QUERY, help="질의마다 받을 결과 수 (기본 20, 최대 50)")
    ap.add_argument("--limit", type=int, default=0, help="표시할 줄 수 (기본 0 = 전부)")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--no-desc", action="store_true", help="설명을 읽지 않는다(빠르지만 이름만 보고 거르게 된다)")
    ap.add_argument("--no-collapse", action="store_true", help="동명 묶음을 접지 않는다")
    a = ap.parse_args()

    jobs = [(q, None) for q in a.queries] + [(q, o) for q in a.queries for o in a.owner]
    if len(jobs) > RATE_LIMIT:
        print(f"# 요청 {len(jobs)}회는 분당 한도({RATE_LIMIT})를 넘는다. 넘친 질의는 1분 기다린 뒤 묻는다.")
    label = lambda j: j[0] + (f" (owner:{j[1]})" if j[1] else "")

    results, wait = {}, 0
    with cf.ThreadPoolExecutor(max_workers=min(6, len(jobs))) as ex:
        for j, (status, val) in zip(jobs, ex.map(lambda j: search(*j, limit=min(a.per_query, 50), timeout=a.timeout), jobs)):
            results[j] = (status, val)
            if status == "limited":
                wait = max(wait, val)
    # 한도에 걸린 질의만, 서버가 알려 준 시간만큼 한 번 기다렸다가 다시 묻는다.
    # 200 응답의 빈 결과는 진짜로 없는 것이니 다시 묻지 않는다(--owner 질의가 비는 것은 흔한 일이다).
    limited = [j for j, (s, _) in results.items() if s == "limited"]
    if limited:
        msg = (f"# 요청 한도에 걸린 질의 {len(limited)}개. {min(wait, 65)}초 뒤 한 번 더 묻는다"
               " (다른 세션이 같은 네트워크에서 검색 중이면 한도를 함께 쓴다). 멈춘 것이 아니다.")
        print(msg, flush=True)
        time.sleep(min(wait, 65))
        for j in limited:
            results[j] = search(*j, limit=min(a.per_query, 50), timeout=a.timeout)

    merged, failed, capped = {}, [], []
    for j in jobs:
        status, val = results[j]
        if status == "limited":
            failed.append(label(j))
            print(f"# 요청 한도로 받지 못함: {label(j)}. '결과 없음'이 아니다. 1분 뒤 이 질의만 다시 돌린다.")
            continue
        if status == "error":
            failed.append(label(j))
            print(f"# 검색 실패: {label(j)} ({val}). 네트워크가 막힌 환경(예: Codex 기본 샌드박스)이면 "
                  "네트워크 허용을 요청한다. 계속 실패하면 https://skills.sh/ 를 웹으로 확인한다.")
            continue
        full = len(val) >= min(a.per_query, 50)
        if full:
            capped.append(label(j))
        print(f"# {'결과 없음' if not val else f'{len(val)}개'}: {label(j)}"
              + (" (이 출처에는 맞는 스킬이 없다)" if j[1] and not val else "")
              + (" (상한에서 잘렸다)" if full else ""))
        for s in val:
            src = s.get("source") or s["id"].rsplit("/", 1)[0]
            key = f"{src}@{s.get('skillId') or s['name']}"
            e = merged.setdefault(key, {"n": s.get("installs") or 0, "id": s["id"], "q": [], "src": src})
            e["n"] = max(e["n"], s.get("installs") or 0)
            if label(j) not in e["q"]:
                e["q"].append(label(j))

    excl = {x.lower() for x in a.exclude}
    is_excluded = lambda k: k.lower() in excl or k.split("@")[0].lower() in excl
    keep = {k: v for k, v in merged.items() if not is_excluded(k) and v["n"] >= a.min_installs}
    nq = lambda v: len({base_query(q) for q in v["q"]})
    # 설치 10회 미만은 맨 뒤로 보낸다. 시험용·찌꺼기 항목이 질의 수만으로 위에 뜨지 않게 하기 위해서다
    rows = sorted(((v["n"], k, v) for k, v in keep.items()), key=lambda r: (r[0] < 10, -nq(r[2]), -r[0], r[1]))
    from find_library import repo_index  # 라이브러리 저장소 표시. 못 읽으면 표시만 빠진다
    lib = repo_index()
    shown = [(r, []) for r in rows] if a.no_collapse else collapse(rows, set(lib))
    visible = shown[: a.limit] if a.limit else shown

    if not a.no_desc and visible:
        ids = [r[2]["id"] for r, _ in visible]
        with cf.ThreadPoolExecutor(max_workers=16) as ex:
            descs = dict(zip(ids, ex.map(describe, ids)))
    else:
        descs = {}

    excluded_names = {k.split("@", 1)[1].lower(): k for k in merged if is_excluded(k)}

    clusters = sum(1 for _, rest in shown if rest)
    print(f"\n# 검색 요약: 질의 {len(a.queries)}개, 요청 {len(jobs)}회"
          + (f"(받지 못한 요청 {len(failed)}회. 후보 수는 부분 결과다)" if failed else "")
          + f" → 후보 {len(rows)}개" + (f", 동명 묶음 {clusters}개를 접어 {len(shown)}줄" if clusters else "")
          + f", 표시 {len(visible)}줄" + (" (전부)" if len(visible) == len(shown) else f" (나머지 {len(shown) - len(visible)}줄은 --limit 0으로 본다)"))
    print("# '검색 범위' 줄에는 '후보 N개 훑음'처럼 실제로 본 줄 수를 쓴다. 정렬: 걸린 질의 수 → 설치 수")
    if capped:
        print(f"# 질의 {len(capped)}개가 결과 상한({min(a.per_query, 50)}개)에서 잘렸다: {', '.join(capped)}."
              " 설치 수가 적은 스킬(라이브러리 카드 등)은 밖에 있을 수 있다. 더 보려면 --per-query 50")
    if clusters:
        print("# '동명 N곳'(이 검색 안)은 이 검색 결과 안에서 같은 이름의 스킬이 있는 저장소 수다. 복사본일 수 있어 설치 수가"
              " 아니라 별과 저장소 나이로 원본을 가린다(find_inspect.py의 신뢰 신호를 본다)")
    print()
    for (n, key, v), rest in visible:
        repo = key.split("@")[0]
        tags = []
        if "/" not in v["src"] or "." in v["src"].split("/")[0]:
            tags.append("GitHub 저장소 아님: find_inspect.py로 확인할 수 없다")
        if repo.lower() in lib:
            tags.append("라이브러리: " + ", ".join(c["name"] for c in lib[repo.lower()][:2]))
        elif any(k.split("@")[0].lower() in lib for _, k, _ in rest):
            tags.append("묶음 안에 라이브러리 카드가 있다")
        if rest:
            owner = repo.split("/")[0].lower()
            others = ", ".join(f"{k.split('@')[0]}({m:,}{', 같은 owner' if k.split('/')[0].lower() == owner else ''})"
                               for m, k, _ in rest[:8]) + (" 외" if len(rest) > 8 else "")
            tags.append(f"동명 {len(rest) + 1}곳(이 검색 안): {others}")
        name = key.split("@", 1)[1].lower()
        if name in excluded_names and excluded_names[name] != key:
            tags.append(f"같은 이름의 {excluded_names[name].split('@')[0]}는 --exclude로 뺐다")
        bases = list(dict.fromkeys(base_query(q) for q in v["q"]))
        owners = sorted({q.split("(owner:")[1].rstrip(")") for q in v["q"] if "(owner:" in q})
        qs = f"질의 {len(bases)}개: " + ", ".join(bases) + (f" [owner 검색: {', '.join(owners)}]" if owners else "")
        desc = descs.get(v["id"], "")
        desc = (desc[:110] + "…") if len(desc) > 110 else desc
        if n < 10:
            tags.append("설치 10회 미만")
        print(f"{n:>9,} | {key} | {qs} | {desc or '-'}" + (f" | [{'; '.join(tags)}]" if tags else "")
              + f" | https://skills.sh/{v['id']}")


if __name__ == "__main__":
    main()
