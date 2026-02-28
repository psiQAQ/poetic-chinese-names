#!/usr/bin/env python3
"""根据 get_chinese_name 与 gushi_namer 生成中文姓名候选。

输出单个 JSON（默认）：
1) outputs/generated_names/generated_names.json
"""

from __future__ import annotations

import argparse
from datetime import datetime
import html
import json
import random
import re
from pathlib import Path
from typing import Dict, Iterable, List


DEFAULT_EXCLUDED_WORDS = (
    "胸鬼懒禽鸟鸡我邪罪凶丑仇鼠蟋蟀淫秽妹狐鸡鸭蝇悔鱼肉苦犬吠窥血丧饥女搔父母昏狗蟊疾病痛"
    "死潦哀痒害蛇牲妇狸鹅穴畜烂兽靡爪氓劫鬣螽毛婚姻匪婆羞辱"
)
DEFAULT_EXCLUDED_FILE = "configs/excluded_chars.txt"

CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
SINGLE_CHAR_RE = re.compile(r"^[\u4e00-\u9fff]$")
SENTENCE_SPLIT_RE = re.compile(r"[！。？；!?\n\r]+")
PUNC_RE = re.compile(r"[<>《》！*\(\^\)\$%~!@#…&%￥—\+=、。，？；‘’“”：·`\s\u3000]")
TAG_RE = re.compile(r"<[^>]+>")

GET_CHINESE_NAME_DATABASES = {
    "gcn_sj": {
        "repo": "get_chinese_name",
        "display": "诗经",
    },
    "gcn_ts": {
        "repo": "get_chinese_name",
        "display": "唐诗",
    },
}

GUSHI_NAMER_DATABASES = {
    "gsn_sj": {
        "repo": "gushi_namer",
        "display": "诗经",
        "book_file": "shijing",
    },
    "gsn_cc": {
        "repo": "gushi_namer",
        "display": "楚辞",
        "book_file": "chuci",
    },
    "gsn_ts": {
        "repo": "gushi_namer",
        "display": "唐诗",
        "book_file": "tangshi",
    },
    "gsn_sc": {
        "repo": "gushi_namer",
        "display": "宋词",
        "book_file": "songci",
    },
    "gsn_yf": {
        "repo": "gushi_namer",
        "display": "乐府",
        "book_file": "yuefu",
    },
    "gsn_gs": {
        "repo": "gushi_namer",
        "display": "古诗",
        "book_file": "gushi",
    },
    "gsn_cf": {
        "repo": "gushi_namer",
        "display": "辞赋",
        "book_file": "cifu",
    },
}

ALL_DATABASES = {**GET_CHINESE_NAME_DATABASES, **GUSHI_NAMER_DATABASES}


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def iter_json_files(directory: Path, pattern: str) -> Iterable[Path]:
    yield from sorted(directory.glob(pattern))


def clean_text(text: str) -> str:
    text = html.unescape(text)
    text = TAG_RE.sub("", text)
    return text


def split_sentences(text: str) -> List[str]:
    text = clean_text(text)
    chunks = [s.strip() for s in SENTENCE_SPLIT_RE.split(text)]
    return [s for s in chunks if len(s) >= 2]


def clean_sentence_for_name(sentence: str) -> str:
    sentence = clean_text(sentence)
    sentence = sentence.replace("（", "").replace("）", "")
    sentence = sentence.replace("(", "").replace(")", "")
    sentence = PUNC_RE.sub("", sentence)
    return sentence


def load_stroke_map(path: Path) -> Dict[str, int]:
    m: Dict[str, int] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) != 3:
                continue
            ch = parts[1]
            try:
                stroke = int(parts[2])
            except ValueError:
                continue
            m[ch] = stroke
    return m


def load_allowed_name_set(
    path: Path, gender_filter: str, given_length: int
) -> set[str]:
    genders: Dict[str, str] = {}
    with path.open("r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) < 2:
                continue
            name = parts[0].strip()
            name_gender = parts[1].strip()
            if not name:
                continue
            if name in genders:
                if genders[name] != name_gender or name_gender == "未知":
                    genders[name] = "双"
            else:
                genders[name] = name_gender
    if gender_filter == "不限":
        return {k for k in genders if len(k) == given_length}
    return {
        k for k, v in genders.items() if v == gender_filter and len(k) == given_length
    }


def stroke_total(name: str, stroke_map: Dict[str, int]) -> int:
    return sum(stroke_map.get(ch, 0) for ch in name)


def load_excluded_chars(path: Path) -> set[str]:
    excluded: set[str] = set()
    if not path.exists():
        return excluded
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            excluded.update(ch for ch in line if CHINESE_RE.match(ch))
    return excluded


def build_excluded_set(excluded_file: Path, excluded_arg: str) -> set[str]:
    excluded = load_excluded_chars(excluded_file)
    if excluded_arg:
        excluded.update(ch for ch in excluded_arg if CHINESE_RE.match(ch))
    return excluded


def resolve_repos_dir(base_dir: Path) -> Path:
    submodules = base_dir / "submodules"
    if submodules.exists():
        return submodules
    return base_dir / "name-repos"


def parse_database_selection(values: List[str]) -> List[str]:
    tokens: List[str] = []
    for value in values:
        for part in value.split(","):
            token = part.strip()
            if token:
                tokens.append(token)

    selected: set[str] = set()
    for token in tokens:
        if token == "all":
            selected.update(ALL_DATABASES.keys())
            continue
        if token == "get_chinese_name":
            selected.update(GET_CHINESE_NAME_DATABASES.keys())
            continue
        if token == "gushi_namer":
            selected.update(GUSHI_NAMER_DATABASES.keys())
            continue
        if token in ALL_DATABASES:
            selected.add(token)
            continue
        raise ValueError(f"未知数据库缩写: {token}")

    if not selected:
        selected.update(ALL_DATABASES.keys())
    return sorted(selected)


def print_database_catalog() -> None:
    print("get_chinese_name 可用数据库:")
    for code in sorted(GET_CHINESE_NAME_DATABASES):
        print(f"  {code}: {GET_CHINESE_NAME_DATABASES[code]['display']}")
    print("gushi_namer 可用数据库:")
    for code in sorted(GUSHI_NAMER_DATABASES):
        print(f"  {code}: {GUSHI_NAMER_DATABASES[code]['display']}")


def is_valid_name(
    name: str, allowed_names: set[str], excluded: set[str], given_length: int
) -> bool:
    if len(name) != given_length:
        return False
    if given_length == 1:
        if not SINGLE_CHAR_RE.match(name):
            return False
    elif not all(CHINESE_RE.match(ch) for ch in name):
        return False
    if allowed_names and name not in allowed_names:
        return False
    if any(ch in excluded for ch in name):
        return False
    return True


def generate_from_get_chinese_name(
    base_dir: Path,
    surname: str,
    gender: str,
    given_length: int,
    selected_databases: set[str],
    count: int,
    allowed_names: set[str],
    excluded: set[str],
    stroke_map: Dict[str, int],
    seed: int,
) -> List[dict]:
    rng = random.Random(seed)
    repos_dir = resolve_repos_dir(base_dir)
    data_dir = repos_dir / "get_chinese_name" / "data"
    results: Dict[str, dict] = {}

    def try_add(
        name: str,
        sentence: str,
        original: str,
        source_library: str,
        source_database_code: str,
        title: str = "",
        book: str = "",
    ):
        if name in results:
            return
        if not is_valid_name(name, allowed_names, excluded, given_length):
            return
        results[name] = {
            "full_name": f"{surname}{name}",
            "first_name": name,
            "gender": gender,
            "stroke_total": stroke_total(name, stroke_map),
            "source_repo": "get_chinese_name",
            "source_library": source_library,
            "source_database_code": source_database_code,
            "hit_sentence": sentence,
            "original_content": original,
            "author": "",
            "title": title,
            "book": book,
            "dynasty": "",
        }

    # 诗经 JSON
    shijing_path = data_dir / "诗经" / "shijing.json"
    if "gcn_sj" in selected_databases and shijing_path.exists():
        shijing = read_json(shijing_path)
        for item in shijing:
            title = str(item.get("title", ""))
            chapter = str(item.get("chapter", ""))
            section = str(item.get("section", ""))
            book = "诗经"
            source_library = f"诗经/{chapter}/{section}".strip("/")
            for para in item.get("content", []) or []:
                sentence = str(para)
                clean = clean_sentence_for_name(sentence)
                for i in range(len(clean) - given_length + 1):
                    try_add(
                        clean[i : i + given_length],
                        sentence,
                        sentence,
                        source_library,
                        source_database_code="gcn_sj",
                        title=title,
                        book=book,
                    )

    # 唐诗 JSON
    tang_dir = data_dir / "唐诗"
    if "gcn_ts" in selected_databases and tang_dir.exists():
        for f in iter_json_files(tang_dir, "poet.tang.*.json"):
            data = read_json(f)
            for item in data:
                title = str(item.get("title", ""))
                author = str(item.get("author", ""))
                for para in item.get("paragraphs", []) or []:
                    sentence = str(para)
                    clean = clean_sentence_for_name(sentence)
                    for i in range(len(clean) - given_length + 1):
                        n = clean[i : i + given_length]
                        if n in results:
                            continue
                        if not is_valid_name(n, allowed_names, excluded, given_length):
                            continue
                        results[n] = {
                            "full_name": f"{surname}{n}",
                            "first_name": n,
                            "gender": gender,
                            "stroke_total": stroke_total(n, stroke_map),
                            "source_repo": "get_chinese_name",
                            "source_library": "唐诗",
                            "source_database_code": "gcn_ts",
                            "hit_sentence": sentence,
                            "original_content": sentence,
                            "author": author,
                            "title": title,
                            "book": "唐诗",
                            "dynasty": "唐",
                        }

    items = list(results.values())
    rng.shuffle(items)
    return items[:count]


def generate_from_gushi_namer(
    base_dir: Path,
    surname: str,
    gender: str,
    given_length: int,
    selected_databases: set[str],
    count: int,
    allowed_names: set[str],
    excluded: set[str],
    stroke_map: Dict[str, int],
    seed: int,
) -> List[dict]:
    rng = random.Random(seed)
    repos_dir = resolve_repos_dir(base_dir)
    json_dir = repos_dir / "gushi_namer" / "public" / "json"
    selected_meta = [
        GUSHI_NAMER_DATABASES[code]
        for code in sorted(selected_databases)
        if code in GUSHI_NAMER_DATABASES
    ]

    passages: List[dict] = []
    for meta in selected_meta:
        db_code = next(
            code
            for code, db in GUSHI_NAMER_DATABASES.items()
            if db["book_file"] == meta["book_file"]
        )
        book_file = meta["book_file"]
        p = json_dir / f"{book_file}.json"
        if not p.exists():
            continue
        data = read_json(p)
        for item in data:
            content = item.get("content")
            if not content:
                continue
            passages.append(
                {
                    "book_file": book_file,
                    "db_code": db_code,
                    "book": str(item.get("book", "")),
                    "title": str(item.get("title", "")),
                    "author": str(item.get("author", "")),
                    "dynasty": str(item.get("dynasty", "")),
                    "content": str(content),
                }
            )

    if not passages:
        return []

    results: Dict[str, dict] = {}
    max_attempts = 300000
    attempts = 0

    while len(results) < count and attempts < max_attempts:
        attempts += 1
        p = rng.choice(passages)
        sents = split_sentences(p["content"])
        if not sents:
            continue
        sent = rng.choice(sents)
        clean = clean_sentence_for_name(sent)
        if len(clean) < given_length:
            continue
        if given_length == 1:
            name = clean[rng.randrange(len(clean))]
        else:
            i = rng.randrange(len(clean))
            j = rng.randrange(len(clean))
            if i == j:
                continue
            if i > j:
                i, j = j, i
            name = clean[i] + clean[j]
        if name in results:
            continue
        if not is_valid_name(name, allowed_names, excluded, given_length):
            continue

        results[name] = {
            "full_name": f"{surname}{name}",
            "first_name": name,
            "gender": gender,
            "stroke_total": stroke_total(name, stroke_map),
            "source_repo": "gushi_namer",
            "source_library": p["book"]
            or GUSHI_NAMER_DATABASES[p["db_code"]]["display"],
            "source_database_code": p["db_code"],
            "hit_sentence": sent,
            "original_content": clean_text(p["content"]),
            "author": p["author"],
            "title": p["title"],
            "book": p["book"],
            "dynasty": p["dynasty"],
        }

    return list(results.values())[:count]


def timestamped_filename(ts: datetime | None = None) -> str:
    current = ts or datetime.now()
    return current.strftime("%Y-%m-%d-%H-%M-%S") + ".json"


def resolve_output_path(base_dir: Path, output_dir: str, output_file: str) -> Path:
    out_dir = base_dir / output_dir
    filename = output_file.strip() or timestamped_filename()
    return out_dir / filename


def build_output_payload(rows: List[dict], settings: Dict) -> Dict:
    return {
        "设置参数": settings,
        "候选姓名": rows,
    }


def merge_and_sample_rows(
    get_rows: List[dict], gushi_rows: List[dict], total_count: int, seed: int
) -> List[dict]:
    combined_rows = get_rows + gushi_rows
    random.Random(seed).shuffle(combined_rows)
    if total_count < 0:
        return []
    return combined_rows[:total_count]


def evaluate_rows_with_chinesenames(rows: List[dict], base_dir: Path) -> List[dict]:
    try:
        from scripts.enrich_generated_names_with_chinesenames import (
            ChineseNamesEvaluator,
        )
    except ModuleNotFoundError:
        from enrich_generated_names_with_chinesenames import ChineseNamesEvaluator

    repos_dir = resolve_repos_dir(base_dir)
    family_csv = repos_dir / "ChineseNames" / "data-csv" / "familyname.csv"
    given_csv = repos_dir / "ChineseNames" / "data-csv" / "givenname.csv"
    evaluator = ChineseNamesEvaluator(family_csv=family_csv, given_csv=given_csv)

    enriched = []
    for item in rows:
        obj = dict(item)
        full_name = obj.get("full_name", "")
        obj["chinesenames_eval"] = evaluator.evaluate_full_name(full_name)
        enriched.append(obj)
    return enriched


def rank_rows(rows: List[dict], top_n: int) -> List[dict]:
    try:
        from scripts.rank_and_localize_names import localize_and_rank_records
    except ModuleNotFoundError:
        from rank_and_localize_names import localize_and_rank_records

    return localize_and_rank_records(rows, top_n=top_n)


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="生成中文姓名候选（get_chinese_name 与 gushi_namer）"
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="项目根目录",
    )
    parser.add_argument("--surname", default="王", help="姓氏，默认王")
    parser.add_argument(
        "--gender",
        default="男",
        choices=["男", "女", "双", "不限"],
        help="性别过滤，默认男",
    )
    parser.add_argument(
        "--given-length",
        type=int,
        default=2,
        choices=[1, 2],
        help="名字字数，支持单字名或双字名，默认2",
    )
    parser.add_argument("--count", type=int, default=50, help="总生成数量")
    parser.add_argument("--seed", type=int, default=20260226, help="随机种子")
    parser.add_argument(
        "--excluded", default="", help="额外排除字符集合（可选，默认不额外追加）"
    )
    parser.add_argument(
        "--excluded-file",
        default=DEFAULT_EXCLUDED_FILE,
        help="排除字符文件（相对 base-dir 或绝对路径）",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="输出目录（相对 base-dir），默认 outputs",
    )
    parser.add_argument(
        "--output-file",
        default="",
        help="输出 JSON 文件名；留空时按年月日时分秒自动命名",
    )
    parser.add_argument(
        "--databases",
        nargs="+",
        default=["all"],
        help=(
            "数据库缩写名，可传一个或多个；支持逗号分隔。"
            "例如 gcn_sj gsn_sc 或 gcn_sj,gsn_sc；"
            "也支持 all/get_chinese_name/gushi_namer"
        ),
    )
    parser.add_argument(
        "--list-databases",
        action="store_true",
        help="仅列出可用数据库与缩写后退出",
    )
    eval_group = parser.add_mutually_exclusive_group()
    eval_group.add_argument(
        "--enable-chinesenames-eval",
        dest="enable_chinesenames_eval",
        action="store_true",
        help="启用 ChineseNames 评估（默认启用）",
    )
    eval_group.add_argument(
        "--disable-chinesenames-eval",
        dest="enable_chinesenames_eval",
        action="store_false",
        help="关闭 ChineseNames 评估",
    )

    rank_group = parser.add_mutually_exclusive_group()
    rank_group.add_argument(
        "--enable-rank",
        dest="enable_rank",
        action="store_true",
        help="启用按名字独特性排序并中文键名化（默认启用）",
    )
    rank_group.add_argument(
        "--disable-rank",
        dest="enable_rank",
        action="store_false",
        help="关闭排序与中文键名化",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=100,
        help="启用排序时保留前 N 个（仅在启用排序时生效）",
    )
    parser.set_defaults(enable_chinesenames_eval=True, enable_rank=True)
    args = parser.parse_args()

    if args.list_databases:
        print_database_catalog()
        return

    if args.count < 0:
        parser.error("--count 必须是非负整数")
    if args.top_n < 0:
        parser.error("--top-n 必须是非负整数")
    if not args.enable_chinesenames_eval:
        args.enable_rank = False

    base_dir = Path(args.base_dir)
    surname = args.surname.strip()
    gender = args.gender
    given_length = args.given_length
    try:
        selected_db_list = parse_database_selection(args.databases)
    except ValueError as e:
        parser.error(str(e))
        return
    selected_db_set = set(selected_db_list)
    repos_dir = resolve_repos_dir(base_dir)
    data_dir = repos_dir / "get_chinese_name" / "data"

    excluded_file = Path(args.excluded_file)
    if not excluded_file.is_absolute():
        excluded_file = base_dir / excluded_file

    allowed_names = load_allowed_name_set(
        data_dir / "Chinese_Names.dat",
        gender_filter=gender,
        given_length=given_length,
    )
    stroke_map = load_stroke_map(data_dir / "stoke.dat")
    excluded = build_excluded_set(excluded_file, args.excluded)

    get_rows = generate_from_get_chinese_name(
        base_dir=base_dir,
        surname=surname,
        gender=gender,
        given_length=given_length,
        selected_databases=selected_db_set,
        count=args.count,
        allowed_names=allowed_names,
        excluded=excluded,
        stroke_map=stroke_map,
        seed=args.seed,
    )
    gushi_rows = generate_from_gushi_namer(
        base_dir=base_dir,
        surname=surname,
        gender=gender,
        given_length=given_length,
        selected_databases=selected_db_set,
        count=args.count,
        allowed_names=allowed_names,
        excluded=excluded,
        stroke_map=stroke_map,
        seed=args.seed + 1,
    )

    output_path = resolve_output_path(
        base_dir=base_dir,
        output_dir=args.output_dir,
        output_file=args.output_file,
    )

    combined_rows = merge_and_sample_rows(
        get_rows=get_rows,
        gushi_rows=gushi_rows,
        total_count=args.count,
        seed=args.seed + 2,
    )
    final_rows = combined_rows
    evaluated_count = 0
    if args.enable_chinesenames_eval:
        final_rows = evaluate_rows_with_chinesenames(final_rows, base_dir)
        evaluated_count = len(final_rows)
    if args.enable_rank:
        final_rows = rank_rows(final_rows, args.top_n)

    settings = {
        "base_dir": str(base_dir),
        "surname": surname,
        "gender": gender,
        "given_length": given_length,
        "count": args.count,
        "seed": args.seed,
        "excluded": args.excluded,
        "excluded_file": str(excluded_file),
        "output_dir": args.output_dir,
        "output_file": output_path.name,
        "selected_databases": selected_db_list,
        "enable_chinesenames_eval": args.enable_chinesenames_eval,
        "enable_rank": args.enable_rank,
        "top_n": args.top_n,
    }
    write_json(output_path, build_output_payload(final_rows, settings))

    use_get = any(code in GET_CHINESE_NAME_DATABASES for code in selected_db_set)
    use_gushi = any(code in GUSHI_NAMER_DATABASES for code in selected_db_set)

    print(f"get_chinese_name: {len(get_rows)} 条")
    print(f"gushi_namer: {len(gushi_rows)} 条")
    print(f"已选择数据库: {', '.join(selected_db_list)}")
    print(f"合并后输出: {len(combined_rows)} 条")
    if args.enable_chinesenames_eval:
        print(f"已启用 ChineseNames 评估: {evaluated_count} 条")
    if args.enable_rank:
        print(f"已启用排序与中文键名化，保留: {len(final_rows)} 条")
    print(f"输出文件: {output_path}")
    if len(combined_rows) < args.count and (use_get or use_gushi):
        print("警告: 总输出未达到目标数量，可调整 seed 或放宽过滤条件。")


if __name__ == "__main__":
    main()
