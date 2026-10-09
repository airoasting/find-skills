#!/usr/bin/env python3
"""find-skills 2단계: 이 컴퓨터에 이미 설치된 스킬을 이름과 설명으로 보여 준다.

`ls`로 폴더 이름만 보면 무엇을 하는 스킬인지 모르고, 스킬이 아닌 폴더(_shared 등)가 섞이고,
폴더가 하나라도 없으면 명령이 실패한 것처럼 끝난다. 이 스크립트는 SKILL.md가 있는 폴더만
골라 frontmatter의 name과 description을 한 줄씩 낸다.

보는 곳:
  Claude Code  ~/.claude/skills, ~/.claude/skills/synced/<계정>/ (claude.ai에서 동기화된 스킬),
               <작업 폴더>/.claude/skills, 설치된 플러그인(~/.claude/plugins)
  Codex        ~/.codex/skills, <작업 폴더>/.codex/skills
  공용         ~/.agents/skills, <작업 폴더>/.agents/skills (skills CLI가 여러 에이전트용으로 까는 곳)

같은 스킬이 여러 위치에 있으면(공용 위치와 Claude Code 위치에 함께 깔린 경우 등) 한 번만 세고
위치를 함께 적는다. 세션이 보여 주는 사용 가능 스킬 목록이 정본이다. 이 출력은 그 목록에 없는 설명을
보거나, 목록을 볼 수 없는 환경(Codex 등)에서 쓰는 보조다.

에이전트마다 읽는 위치가 다르다. Claude Code는 Claude Code 위치와 플러그인을, Codex는 Codex 위치와 공용
위치를 읽는다. --agent로 지금 돌고 있는 에이전트를 넘기면 그 에이전트가 실제로 쓸 수 있는 스킬만 센다.

사용법:
  python3 scripts/find_installed.py --agent claude-code
  python3 scripts/find_installed.py --agent codex --grep "slide|ppt|deck"
"""
import argparse
import json
import pathlib
import re

HOME = pathlib.Path.home()
CWD = pathlib.Path.cwd()


def front(text):
    """frontmatter의 name, description(여러 줄 블록 포함)."""
    fm = text.split("\n---", 1)[0] if text.startswith("---") else ""
    name = re.search(r"^name:\s*['\"]?([^'\"\n]+)", fm, re.M)
    m = re.search(r"^description:[ \t]*(.*)\n((?:[ \t]+.*\n?)*)", fm + "\n", re.M)
    desc = ""
    if m:
        desc = m.group(1).strip()
        if desc.rstrip("-") in (">", "|", ""):
            desc = " ".join(l.strip() for l in m.group(2).splitlines())
    return (name.group(1).strip() if name else ""), desc.strip("'\" ")


def skills_in(folder, depth=1):
    """folder 아래 depth 단계 안에 있는 SKILL.md들."""
    if not folder.is_dir():
        return []
    pattern = "/".join(["*"] * depth) + "/SKILL.md"
    return sorted(set(folder.glob(pattern)) | (set(folder.glob("SKILL.md")) if depth == 0 else set()))


def plugin_skills():
    """설치된 Claude Code 플러그인이 담은 스킬. (플러그인 이름, SKILL.md 경로) 목록.
    claude.ai에서 동기화된 플러그인(~/.claude/plugins/synced/<계정>/<플러그인>/skills/)도 포함한다."""
    reg = HOME / ".claude" / "plugins" / "installed_plugins.json"
    out = []
    synced = HOME / ".claude" / "plugins" / "synced"
    if synced.is_dir():
        for md in sorted(synced.glob("*/*/skills/*/SKILL.md")):
            out.append((md.parents[2].name.split("~")[0], md))
    try:
        plugins = json.loads(reg.read_text()).get("plugins", {})
    except Exception:
        return out
    for pname, installs in plugins.items():
        for inst in installs if isinstance(installs, list) else [installs]:
            root = pathlib.Path(inst.get("installPath", ""))
            if root.is_dir():
                for p in sorted(root.glob("**/SKILL.md")):
                    if "node_modules" not in p.parts:
                        out.append((pname, p))
    return out


READS = {  # 에이전트가 읽는 위치(위치 이름의 앞부분)
    "claude-code": ("Claude Code", "플러그인"),
    "codex": ("Codex", "공용"),
}


def collect():
    """[(위치 이름, 스킬 이름, 설명, SKILL.md 경로)]. 스킬 아닌 폴더 수도 함께 돌려준다."""
    places = [
        ("Claude Code", HOME / ".claude" / "skills", 1), ("Claude Code(동기화)", HOME / ".claude" / "skills" / "synced", 2),
        ("Claude Code(프로젝트)", CWD / ".claude" / "skills", 1),
        ("Codex", HOME / ".codex" / "skills", 1), ("Codex(프로젝트)", CWD / ".codex" / "skills", 1),
        ("공용(skills CLI)", HOME / ".agents" / "skills", 1), ("공용(프로젝트)", CWD / ".agents" / "skills", 1),
    ]
    rows, skipped, seen = [], {}, set()
    for label, folder, depth in places:
        if not folder.is_dir():
            continue
        key = folder.resolve()
        if key in seen:
            continue
        seen.add(key)
        if depth == 1:
            skipped[label] = [d.name for d in folder.iterdir()
                              if d.is_dir() and not (d / "SKILL.md").exists() and d.name != "synced"]
        for md in skills_in(folder, depth):
            name, desc = front(md.read_text(errors="replace"))
            rows.append((label, name or md.parent.name, desc, md))
    for pname, md in plugin_skills():
        name, desc = front(md.read_text(errors="replace"))
        rows.append((f"플러그인 {pname.split('@')[0]}", f"{pname.split('@')[0]}:{name or md.parent.name}", desc, md))
    return rows, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grep", help="이름·설명에 이 정규식이 든 스킬만 (대소문자 무시)")
    ap.add_argument("--width", type=int, default=140, help="설명을 이 글자 수에서 자른다")
    ap.add_argument("--agent", choices=["claude-code", "codex", "all"], default="all",
                    help="지금 돌고 있는 에이전트. 그 에이전트가 읽는 위치만 센다 (기본 all)")
    a = ap.parse_args()
    pat = re.compile(a.grep, re.I) if a.grep else None

    rows, skipped = collect()
    if a.agent != "all":
        rows = [r for r in rows if r[0].startswith(READS[a.agent])]
        skipped = {k: v for k, v in skipped.items() if k.startswith(READS[a.agent])}
    # 같은 스킬(이름과 설명이 같다)은 한 번만 세고 위치를 모은다
    merged = {}
    for label, name, desc, md in rows:
        # 플러그인 접두사(hyperframes:)를 뗀 이름으로 묶는다. 같은 스킬이 폴더와 플러그인 양쪽에 깔린 경우다
        e = merged.setdefault((name.split(":")[-1].lower(), desc[:200]), {"name": name, "desc": desc, "where": []})
        if label not in e["where"]:
            e["where"].append(label)
    shown = 0
    for e in merged.values():
        text = f"{e['name']} {e['desc']}"
        m = pat.search(text) if pat else None
        if pat and not m:
            continue
        shown += 1
        desc = e["desc"][:a.width] + ("…" if len(e["desc"]) > a.width else "")
        hit = ""
        if m and m.start() > len(e["name"]) + a.width:  # 걸린 말이 잘린 설명 뒤쪽에 있으면 보여 준다
            hit = f" [일치: …{text[max(0, m.start() - 20): m.end() + 20]}…]"
        print(f"- {e['name']} | {desc}{hit} | 위치: {', '.join(e['where'])}")
    if not shown:
        print("- (걸린 것 없음)" if pat else "- (설치된 스킬 없음)")
    for label, names in skipped.items():
        if names:
            print(f"# {label}: 스킬이 아닌 폴더 {len(names)}개는 뺐다({', '.join(names[:5])})")
    print(f"\n# {'모든 에이전트' if a.agent == 'all' else a.agent}에 설치된 스킬 {len(merged)}개(위치가 여러 곳인 것은 한 번만 셈)"
          + (f" 중 {shown}개가 '{a.grep}'에 걸림" if pat else "")
          + ". 세션의 사용 가능 스킬 목록이 있으면 그쪽이 정본이다. '검색 범위' 줄에는 세션 목록이 있으면 그 수를,"
          " 없으면 이 수를 쓴다")


if __name__ == "__main__":
    main()
