#!/usr/bin/env python3
"""用 ChineseNames 数据评估已生成姓名并补充到 JSON。"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional


def resolve_repos_dir(base_dir: Path) -> Path:
    submodules = base_dir / "submodules"
    if submodules.exists():
        return submodules
    return base_dir / "name-repos"


def _to_float(v: Optional[str]) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _round_float(v: Optional[float], digits: int = 4) -> Optional[float]:
    if v is None:
        return None
    return round(v, digits)


class ChineseNamesEvaluator:
    def __init__(self, family_csv: Path, given_csv: Path):
        self.family_map = self._load_family(family_csv)
        self.given_map = self._load_given(given_csv)

    @staticmethod
    def _clean_keys(row: Dict[str, str]) -> Dict[str, str]:
        return {k.lstrip("\ufeff"): v for k, v in row.items()}

    def _load_family(self, path: Path) -> Dict[str, Dict[str, str]]:
        out: Dict[str, Dict[str, str]] = {}
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                r = self._clean_keys(row)
                surname = r.get("surname", "")
                if surname:
                    out[surname] = r
        return out

    def _load_given(self, path: Path) -> Dict[str, Dict[str, str]]:
        out: Dict[str, Dict[str, str]] = {}
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                r = self._clean_keys(row)
                ch = r.get("character", "")
                if ch:
                    out[ch] = r
        return out

    def evaluate_full_name(self, full_name: str) -> Dict:
        if len(full_name) < 2:
            return {
                "可用": False,
                "提示": ["姓名长度不足"],
                "覆盖字数": 0,
            }

        surname = full_name[0]
        given_chars = list(full_name[1:])
        surname_row = self.family_map.get(surname)

        char_metrics: List[Dict] = []
        found_rows = []
        for ch in given_chars:
            row = self.given_map.get(ch)
            if row:
                found_rows.append(row)
                char_metrics.append(
                    {
                        "字符": ch,
                        "名字独特性": _to_float(row.get("name.uniqueness")),
                        "语料独特性": _to_float(row.get("corpus.uniqueness")),
                        "性别倾向": _to_float(row.get("name.gender")),
                        "积极度": _to_float(row.get("name.valence")),
                        "温暖度": _to_float(row.get("name.warmth")),
                        "能力感": _to_float(row.get("name.competence")),
                    }
                )
            else:
                char_metrics.append({"字符": ch, "缺失": True})

        def avg(field: str) -> Optional[float]:
            vals = [_to_float(r.get(field)) for r in found_rows]
            vals = [v for v in vals if v is not None]
            return mean(vals) if vals else None

        indices_raw = {
            "NLen": len(full_name),
            "SNU": _to_float(surname_row.get("surname.uniqueness"))
            if surname_row
            else None,
            "SNI": _to_float(surname_row.get("initial.rank")) if surname_row else None,
            "NU": avg("name.uniqueness"),
            "CCU": avg("corpus.uniqueness"),
            "NG": avg("name.gender"),
            "NV": avg("name.valence"),
            "NW": avg("name.warmth"),
            "NC": avg("name.competence"),
        }

        index_name_map = {
            "NLen": "姓名长度",
            "SNU": "姓氏独特性",
            "SNI": "姓氏首字母序位",
            "NU": "名字用字独特性",
            "CCU": "语料字独特性",
            "NG": "名字性别倾向",
            "NV": "名字积极度",
            "NW": "名字温暖度",
            "NC": "名字能力感",
        }
        indices = {index_name_map[k]: v for k, v in indices_raw.items()}
        indices = {
            k: _round_float(v, 4) if isinstance(v, float) else v
            for k, v in indices.items()
        }

        coverage = len(found_rows)
        full_coverage = coverage == len(given_chars)

        reasons = []
        if not full_coverage:
            reasons.append("部分字符未命中 ChineseNames")
        if indices_raw["NG"] is not None and indices_raw["NG"] < 0:
            reasons.append("性别倾向偏女性")
        if indices_raw["NV"] is not None and indices_raw["NV"] < 2.8:
            reasons.append("积极度偏低")

        usable = (
            full_coverage
            and (indices_raw["NG"] is None or indices_raw["NG"] >= 0)
            and (indices_raw["NV"] is None or indices_raw["NV"] >= 2.8)
        )

        return {
            "可用": usable,
            "覆盖字数": coverage,
            "姓氏信息": {
                "姓氏": surname,
                "姓氏独特性": _round_float(indices_raw["SNU"], 4),
                "姓氏首字母序位": _round_float(indices_raw["SNI"], 4),
            },
            "指标": indices,
            "逐字指标": char_metrics,
            "提示": reasons,
            "数据来源": "ChineseNames（1930-2008）",
        }


def enrich_json_file(
    input_json: Path, output_json: Path, evaluator: ChineseNamesEvaluator
) -> None:
    data = json.loads(input_json.read_text(encoding="utf-8"))
    enriched = []
    for item in data:
        obj = dict(item)
        full_name = obj.get("full_name", "")
        obj["chinesenames_eval"] = evaluator.evaluate_full_name(full_name)
        enriched.append(obj)
    output_json.write_text(
        json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="用 ChineseNames 评估已生成姓名 JSON")
    parser.add_argument(
        "--base-dir",
        default=".",
        help="项目根目录",
    )
    parser.add_argument(
        "--input-files",
        nargs="+",
        default=[
            "outputs/generated_names/generated_names.json",
        ],
        help="待评估 JSON 文件（相对 base-dir）",
    )
    parser.add_argument(
        "--output-suffix",
        default="",
        help="输出文件后缀，默认空表示原地覆盖；例如 _evaluated",
    )
    args = parser.parse_args()

    base = Path(args.base_dir)
    repos_dir = resolve_repos_dir(base)
    family_csv = repos_dir / "ChineseNames" / "data-csv" / "familyname.csv"
    given_csv = repos_dir / "ChineseNames" / "data-csv" / "givenname.csv"
    evaluator = ChineseNamesEvaluator(family_csv=family_csv, given_csv=given_csv)

    for rel in args.input_files:
        input_path = base / rel
        if args.output_suffix:
            output_path = input_path.with_name(
                input_path.stem + args.output_suffix + input_path.suffix
            )
        else:
            output_path = input_path
        enrich_json_file(
            input_json=input_path, output_json=output_path, evaluator=evaluator
        )
        print(f"已输出: {output_path}")


if __name__ == "__main__":
    main()
