#!/usr/bin/env python3
"""Create product comparison files from item JSON.

Standalone v2: C0 variant output groups gtin, price, and selector_values by variant.

Usage:
    python3 tools/mk_product_info4compare_v2.py -f 100_冷蔵庫.json -c1
    python3 tools/mk_product_info4compare_v2.py -f 100_冷蔵庫.json -c1 -tsv
    python3 tools/mk_product_info4compare_v2.py -c0 -dir ../data/refrigerator/output
    python3 tools/mk_product_info4compare_v2.py -c0 -dir ../data/refrigerator/output -full
    python3 tools/mk_product_info4compare_v2.py -dir ../data/aircon/output_gmc_c2/ -c2 -outdir ./c2
"""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
from typing import Any


PRODUCT_FACT_KEY_LABELS = {
    "product_name": "製品名",
    "product_series": "製品シリーズ",
    "brand": "ブランド",
    "base_model": "モデル",
    "mpn": "メーカー型番",
    "product_type": "製品タイプ",
    "color": "製品カラー",
    "size": "サイズ",
    "shape_summary": "形状",
    "standard_features": "製品の標準特徴",
    "additional_features": "製品の特徴その２",
    "hero_material": "主な素材",
    "specification": "仕様",
    "weight": "重量",
    "dimension": "寸法",
    "dimensions": "寸法",
    "country_of_origin": "生産国",
    "materials": "素材",
    "instruction": "取扱説明",
    "instructions": "取扱説明",
    "warnings": "注意事項",
    "variant_prices": "値段",
    "variant_price": "値段",
    "selector_values": "選択属性",
}

C1_FIELDS = [
    "shop_id",
    "itm_id",
    "title",
    "tagline",
    "precautions",
    "description",
    "product_description",
    "sp_caption",
    "genre_name",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("-c0", action="store_true", help="create C0 JSON files")
    mode.add_argument("-c1", action="store_true", help="create C1 files")
    mode.add_argument("-c2", action="store_true", help="copy C2 JSON files with _c2 suffix")
    parser.add_argument("-f", "--file", default=None, help="input JSON file for -c1")
    parser.add_argument(
        "-dir",
        "--dir",
        dest="input_dir",
        default=None,
        help="input directory for -c0/-c2",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        "-outdir",
        dest="output_dir",
        default=None,
        help="output directory (default: ./c0 for -c0, <input_dir>/c1 for -c1)",
    )
    parser.add_argument(
        "-full",
        action="store_true",
        help="for -c0, recursively extract all value fields under product_facts",
    )
    parser.add_argument(
        "-tsv",
        action="store_true",
        help="for -c1, write TSV files instead of the default JSON files",
    )
    return parser.parse_args()


def clean_text(value: Any) -> str:
    """Return a single-line TSV-safe representation."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    return " ".join(text.replace("\t", " ").splitlines()).strip()


def load_json_string(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def format_values(values: Any) -> str:
    values = load_json_string(values)
    if values is None:
        return ""
    if isinstance(values, list):
        return ", ".join(clean_text(v) for v in values)
    return clean_text(values)


def format_attributes(attributes: Any) -> str:
    """Format SKU attributes as '<name> : <values> ; ...'."""
    attributes = load_json_string(attributes)
    if attributes in (None, "null", ""):
        return ""
    if not isinstance(attributes, list):
        return clean_text(attributes)

    formatted = []
    for attr in attributes:
        attr = load_json_string(attr)
        if not isinstance(attr, dict):
            continue
        name = clean_text(attr.get("name"))
        values = format_values(attr.get("values"))
        if name:
            formatted.append(f"{name} : {values}")
    return " ; ".join(formatted)


def format_sku_detail(sku: Any) -> str:
    if not isinstance(sku, dict):
        return clean_text(sku)

    sku_info = clean_text(sku.get("sku_info"))
    standard_price = clean_text(sku.get("standard_price"))
    if standard_price:
        standard_price = f"{standard_price}円"
    attributes = format_attributes(sku.get("attributes"))

    parts = [sku_info, standard_price, attributes]
    parts = [part for part in parts if part]
    return " / ".join(parts)


def output_c1_filename(item: dict[str, Any], index: int) -> str:
    shop_id = clean_text(item.get("shop_id")) or f"shop{index + 1}"
    item_id = clean_text(item.get("item_id") or item.get("itm_id")) or f"item{index + 1}"
    return f"{shop_id}__{item_id}_c1.tsv"


def output_c1_json_filename(item: dict[str, Any], index: int) -> str:
    shop_id = clean_text(item.get("shop_id")) or f"shop{index + 1}"
    item_id = clean_text(item.get("item_id") or item.get("itm_id")) or f"item{index + 1}"
    return f"{shop_id}__{item_id}_c1.json"


def make_c1_data(item: dict[str, Any]) -> dict[str, Any]:
    c1_data: dict[str, Any] = {}
    for key in C1_FIELDS:
        if key == "itm_id":
            value = item.get("itm_id", item.get("item_id"))
        else:
            value = item.get(key)
        c1_data[key] = clean_text(value)

    sku_details = load_json_string(item.get("sku_details"))
    if isinstance(sku_details, list):
        for sku_index, sku in enumerate(sku_details, start=1):
            c1_data[f"sku_detail{sku_index}"] = format_sku_detail(sku)
    elif sku_details not in (None, "null", ""):
        c1_data["sku_detail1"] = format_sku_detail(sku_details)

    return c1_data


def write_c1_tsv_file(item: dict[str, Any], index: int, output_dir: Path) -> Path:
    output_path = output_dir / output_c1_filename(item, index)
    with output_path.open("w", encoding="utf-8") as f:
        for key, value in make_c1_data(item).items():
            f.write(f"{key}\t{clean_text(value)}\n")

    return output_path


def write_c1_json_file(item: dict[str, Any], index: int, output_dir: Path) -> Path:
    output_path = output_dir / output_c1_json_filename(item, index)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(make_c1_data(item), f, ensure_ascii=False, indent=2)
        f.write("\n")
    return output_path


def create_c1_files(input_path: Path, output_dir: Path, tsv: bool = False) -> list[Path]:
    with input_path.open(encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("input JSON must be an array of item objects")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_files = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        if tsv:
            output_files.append(write_c1_tsv_file(item, index, output_dir))
        else:
            output_files.append(write_c1_json_file(item, index, output_dir))
    return output_files


def get_product_facts(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}

    product_facts = data.get("product_fact")
    if product_facts is None:
        product_facts = data.get("product_facts")
    if not isinstance(product_facts, dict):
        return {}

    return product_facts


def extract_value_tree(value: Any) -> Any:
    """Recursively replace dicts that contain value with their value payload."""
    if isinstance(value, dict):
        if "value" in value:
            return extract_value_tree(value["value"])
        return {key: extract_value_tree(child) for key, child in value.items()}
    if isinstance(value, list):
        return [extract_value_tree(child) for child in value]
    return value


def extract_product_facts(data: Any, full: bool = False) -> dict[str, Any]:
    product_facts = get_product_facts(data)
    if not product_facts:
        return {}

    if full:
        return extract_value_tree(deepcopy(product_facts))

    extracted: dict[str, Any] = {}
    for key, fact in product_facts.items():
        if isinstance(fact, dict) and "value" in fact:
            extracted[key] = fact["value"]
        else:
            extracted[key] = fact
    return extracted


def rename_product_fact_keys(product_facts: dict[str, Any]) -> dict[str, Any]:
    renamed: dict[str, Any] = {}
    for key, value in product_facts.items():
        renamed[PRODUCT_FACT_KEY_LABELS.get(key, key)] = value
    return renamed


def walk_json(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def collect_price_values(value: Any) -> list[Any]:
    prices = []
    for node in walk_json(value):
        if isinstance(node, dict) and "price" in node:
            price = node["price"]
            if isinstance(price, list):
                prices.extend(price)
            else:
                prices.append(price)
    return prices


def collect_selector_values(value: Any) -> list[Any]:
    selector_values = []
    for node in walk_json(value):
        if isinstance(node, dict) and "selector_values" in node:
            selector_value = node["selector_values"]
            if isinstance(selector_value, list):
                selector_values.extend(selector_value)
            else:
                selector_values.append(selector_value)
    return selector_values


def extract_variant_prices(data: Any) -> list[str]:
    variant_roots = []
    for node in walk_json(data):
        if not isinstance(node, dict):
            continue
        for key in ("variant", "variants"):
            if key in node:
                variant_roots.append(node[key])

    prices = []
    for root in variant_roots:
        for price in collect_price_values(root):
            price_text = clean_text(price)
            if not price_text:
                continue
            if not price_text.endswith("円"):
                price_text = f"{price_text}円"
            prices.append(price_text)
    return prices


def extract_selector_values(data: Any) -> list[str]:
    variant_roots = []
    for node in walk_json(data):
        if not isinstance(node, dict):
            continue
        for key in ("variant", "variants"):
            if key in node:
                variant_roots.append(node[key])

    selector_values = []
    for root in variant_roots:
        for selector_value in collect_selector_values(root):
            selector_text = clean_text(selector_value)
            if selector_text:
                selector_values.append(selector_text)
    return selector_values



def iter_variant_items(value: Any):
    """Yield individual variant dicts from variant/variants blocks."""
    for node in walk_json(value):
        if not isinstance(node, dict):
            continue
        for key in ("variant", "variants"):
            variants = node.get(key)
            if isinstance(variants, list):
                for variant in variants:
                    if isinstance(variant, dict):
                        yield variant
            elif isinstance(variants, dict):
                variant_values = variants.get("value")
                if isinstance(variant_values, list):
                    for variant in variant_values:
                        if isinstance(variant, dict):
                            yield variant
                else:
                    yield variants


def is_variant_item(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return any(key in value for key in ("gtin", "selector_values")) or isinstance(
        value.get("price"), str
    )


def format_price(value: Any) -> str:
    price_text = clean_text(value)
    if price_text and not price_text.endswith("円"):
        price_text = f"{price_text}円"
    return price_text


def extract_variant_products(data: Any) -> dict[str, dict[str, Any]]:
    variant_products: dict[str, dict[str, Any]] = {}
    variants = [variant for variant in iter_variant_items(data) if is_variant_item(variant)]
    for index, variant in enumerate(variants, start=1):
        variant_products[f"個別商品{index}"] = {
            "gtin": clean_text(variant.get("gtin")),
            "値段": format_price(variant.get("price")),
            "個別属性": variant.get("selector_values", []),
        }
    return variant_products


def make_c0_data(data: Any, full: bool = False) -> dict[str, Any]:
    product_facts = rename_product_fact_keys(
        extract_product_facts(data, full=full)
    )
    product_facts.update(extract_variant_products(data))
    return product_facts


def output_c0_path(input_dir: Path, json_path: Path, output_dir: Path) -> Path:
    relative = json_path.relative_to(input_dir)
    return output_dir / relative.parent / f"{relative.stem}_c0.json"


def write_c0_file(
    input_dir: Path,
    json_path: Path,
    output_dir: Path,
    full: bool = False,
) -> Path:
    with json_path.open(encoding="utf-8") as f:
        data = json.load(f)

    output_path = output_c0_path(input_dir, json_path, output_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(make_c0_data(data, full=full), f, ensure_ascii=False, indent=2)
        f.write("\n")
    return output_path


def create_c0_files(input_dir: Path, output_dir: Path, full: bool = False) -> list[Path]:
    if not input_dir.is_dir():
        raise ValueError(f"input directory does not exist: {input_dir}")

    output_files = []
    for json_path in sorted(input_dir.rglob("*.json")):
        if output_dir in json_path.parents:
            continue
        output_files.append(write_c0_file(input_dir, json_path, output_dir, full=full))
    return output_files


def output_c2_path(input_root: Path, json_path: Path, output_dir: Path) -> Path:
    relative_parent = json_path.relative_to(input_root).parent
    stem = json_path.stem
    if not stem.endswith("_c2"):
        stem = f"{stem}_c2"
    return output_dir / relative_parent / f"{stem}.json"


def iter_c2_input_files(input_path: Path) -> list[Path]:
    if not input_path.is_dir():
        raise ValueError(f"input directory does not exist: {input_path}")
    return sorted(input_path.rglob("*.json"))


def create_c2_files(input_path: Path, output_dir: Path) -> list[Path]:
    output_files = []
    for json_path in iter_c2_input_files(input_path):
        if output_dir in json_path.parents:
            continue
        output_path = output_c2_path(input_path, json_path, output_dir)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(json_path, output_path)
        output_files.append(output_path)
    return output_files


def main() -> None:
    args = parse_args()

    if args.c1:
        if not args.file:
            raise SystemExit("-c1 requires -f/--file")
        input_path = Path(args.file).expanduser().resolve()
        output_dir = (
            Path(args.output_dir).expanduser().resolve()
            if args.output_dir
            else input_path.parent / "c1"
        )
        output_files = create_c1_files(input_path, output_dir, tsv=args.tsv)
        file_type = "TSV" if args.tsv else "JSON"
        print(f"created {len(output_files)} C1 {file_type} files under {output_dir}")
        return

    if args.c2:
        if not args.input_dir:
            raise SystemExit("-c2 requires -dir/--dir")
        input_path = Path(args.input_dir).expanduser().resolve()
        output_dir = (
            Path(args.output_dir).expanduser().resolve()
            if args.output_dir
            else Path.cwd() / "c2"
        )
        output_files = create_c2_files(input_path, output_dir)
        print(f"created {len(output_files)} C2 files under {output_dir}")
        return

    if not args.input_dir:
        raise SystemExit("-c0 requires -dir/--dir")
    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = (
        Path(args.output_dir).expanduser().resolve()
        if args.output_dir
        else Path.cwd() / "c0"
    )
    output_files = create_c0_files(input_dir, output_dir, full=args.full)
    mode = "full" if args.full else "light"
    print(f"created {len(output_files)} C0 files ({mode}) under {output_dir}")


if __name__ == "__main__":
    main()
