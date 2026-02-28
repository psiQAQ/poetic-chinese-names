#!/usr/bin/env python3
"""将姓名结果本地化为全中文键，并按最大名字独特性排序保留前N条。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List


TOP_LEVEL_MAP = {
    "full_name": "姓名",
    "first_name": "名字",
    "gender": "性别",
    "stroke_total": "名字笔画总数",
    "source_repo": "来源仓库",
    "source_library": "使用库名称",
    "source_database_code": "来源数据库缩写",
    "hit_sentence": "命中句子",
    "original_content": "原文",
    "author": "作者",
    "title": "篇名",
    "book": "书名",
    "dynasty": "朝代",
    "chinesenames_eval": "评估",
}


def _max_name_uniqueness(rec: Dict) -> float:
    eval_obj = rec.get("chinesenames_eval") or rec.get("评估") or {}
    chars = eval_obj.get("逐字指标", [])
    vals = []
    for c in chars:
        v = c.get("名字独特性")
        if isinstance(v, (int, float)):
            vals.append(float(v))
    return max(vals) if vals else float("-inf")


def localize_and_rank_records(records: List[Dict], top_n: int) -> List[Dict]:
    ranked = sorted(records, key=_max_name_uniqueness, reverse=True)
    kept = ranked[:top_n]

    out = []
    for rec in kept:
        obj = {}
        for k, v in rec.items():
            obj[TOP_LEVEL_MAP.get(k, k)] = v
        obj["排序依据_最大名字独特性"] = round(_max_name_uniqueness(rec), 4)
        out.append(obj)
    return out


def process_file(path: Path, top_n: int) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    output = localize_and_rank_records(data, top_n=top_n)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已处理: {path}，保留 {len(output)} 条")


def main() -> None:
    parser = argparse.ArgumentParser(description="结果本地化并按名字独特性排序")
    parser.add_argument(
        "--base-dir",
        default=".",
        help="项目根目录",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        default=[
            "outputs/generated_names/generated_names.json",
        ],
        help="待处理 JSON 文件（相对 base-dir）",
    )
    parser.add_argument("--top-n", type=int, default=100, help="排序后保留数量")
    args = parser.parse_args()

    base = Path(args.base_dir)
    for rel in args.files:
        process_file(base / rel, top_n=args.top_n)


if __name__ == "__main__":
    main()
