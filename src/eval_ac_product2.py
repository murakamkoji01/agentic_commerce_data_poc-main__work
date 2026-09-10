#!/usr/bin/env python3
"""Evaluate Agentic Commerce product retrieval experiment results.

v2: prediction rows whose first column is not "YES"/"NO" are treated as
having no result (excluded from predictions) instead of raising an error.
Such rows are counted as "Output Failure" and reported after the token
summary.

Usage:
    python3 tools/eval_ac_product2.py -f QuestionExamples_v1_organized_GTv1.tsv -dir exp0813a -type c0
"""

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


PRODUCT_ID_PATTERN = re.compile(
    r"(\d+__\d+)(?:_(?:c0|c1|c2))?\.(?:json|tsv)$",
    re.IGNORECASE,
)
TOKEN_FIELD_PATTERN = re.compile(r"^\d+\s*[,/]\s*\d+\s*[,/]\s*\d+$")
ANSWER_PATTERN = re.compile(r'^"*(YES|NO)"*$', re.IGNORECASE)


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            reasoning_tokens=self.reasoning_tokens + other.reasoning_tokens,
        )


@dataclass
class ParsedRow:
    status: str  # "ok" or "output_failure"
    answer: Optional[str]
    product_id: Optional[str]
    tokens: TokenUsage


@dataclass
class GroundTruth:
    question_id: str
    question_type: str
    question: str
    gtins: str
    product_ids: set[str]


@dataclass
class QuestionMetrics:
    question_id: str
    question: str
    gt_count: int
    output_count: int
    tp_count: int
    recall: float
    precision: float
    fscore: float
    tp: int
    fp: int
    fn: int
    tokens: TokenUsage
    output_failures: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-f", "--file", required=True, help="ground truth TSV file")
    parser.add_argument(
        "-dir",
        "--dir",
        dest="result_dir",
        required=True,
        help="directory containing result TSV files",
    )
    parser.add_argument(
        "-type",
        "--type",
        dest="data_type",
        required=True,
        choices=["c0", "c1", "c2"],
        help="result data type",
    )
    return parser.parse_args()


def normalize_question_id(question_id: str) -> str:
    return question_id.strip().lower()


def parse_id_list(value: str) -> set[str]:
    return {
        item.strip()
        for item in (value or "").replace("，", ",").split(",")
        if item.strip()
    }


def load_ground_truth(path: Path) -> dict[str, GroundTruth]:
    ground_truths = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 5:
                continue
            question_id = normalize_question_id(row[0])
            ground_truths[question_id] = GroundTruth(
                question_id=question_id,
                question_type=row[1].strip(),
                question=row[2].strip(),
                gtins=row[3].strip(),
                product_ids=parse_id_list(row[4]),
            )
    if not ground_truths:
        raise ValueError(f"no ground truth rows found in: {path}")
    return ground_truths


def extract_product_id(path_text: str) -> Optional[str]:
    match = PRODUCT_ID_PATTERN.search(path_text.strip())
    if not match:
        return None
    return match.group(1)


def normalize_answer(raw_answer: str) -> str:
    text = raw_answer.strip()
    for _ in range(2):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            break
        if isinstance(parsed, dict):
            answer_value = parsed.get("answer")
            if isinstance(answer_value, str):
                text = answer_value.strip()
                break
            return text.upper()
        if isinstance(parsed, str):
            text = parsed.strip()
            continue
        return text.upper()

    match = ANSWER_PATTERN.fullmatch(text)
    if match:
        return match.group(1).upper()
    return text.upper()


def parse_tokens(token_text: str) -> TokenUsage:
    text = token_text.strip()
    separator = "/" if "/" in text else ","
    parts = [part.strip() for part in text.split(separator)]
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"invalid token field: {token_text}")
    return TokenUsage(
        input_tokens=int(parts[0]),
        output_tokens=int(parts[1]),
        reasoning_tokens=int(parts[2]),
    )


def parse_result_row(row: list[str]) -> ParsedRow:
    if len(row) < 3:
        raise ValueError(f"invalid result row: {row}")

    raw_answer = row[0].strip()
    answer = normalize_answer(raw_answer)
    fields = [field.strip() for field in row]
    tokens = TokenUsage()
    search_fields = fields[1:]

    if len(fields) >= 4 and TOKEN_FIELD_PATTERN.match(fields[1]):
        tokens = parse_tokens(fields[1])
        search_fields = fields[2:]

    if answer not in {"YES", "NO"}:
        # First column is not YES/NO: treat as no result ("Output Failure")
        # rather than raising, but still account for any tokens consumed.
        path_field = next(
            (field for field in search_fields if PRODUCT_ID_PATTERN.search(field)),
            "",
        )
        product_id = extract_product_id(path_field) if path_field else None
        return ParsedRow(
            status="output_failure",
            answer=raw_answer,
            product_id=product_id,
            tokens=tokens,
        )

    path_field = next(
        (field for field in search_fields if PRODUCT_ID_PATTERN.search(field)),
        "",
    )
    if not path_field:
        raise ValueError(f"could not find product path in row: {row}")

    return ParsedRow(
        status="ok",
        answer=answer,
        product_id=extract_product_id(path_field),
        tokens=tokens,
    )


def find_result_file(result_dir: Path, question_id: str, data_type: str) -> Path:
    patterns = [
        f"res_{question_id}__{data_type}_*.tsv",
        f"res_{question_id}_{data_type}_*.tsv",
        f"res_q_{question_id}__{data_type}_*.tsv",
        f"res_q_{question_id}_{data_type}_*.tsv",
    ]
    for pattern in patterns:
        matches = sorted(result_dir.glob(pattern))
        if matches:
            return matches[0]
    raise FileNotFoundError(
        f"result file not found for {question_id} under {result_dir}"
    )


def load_predictions(result_path: Path) -> tuple[dict[str, str], TokenUsage, int]:
    predictions: dict[str, str] = {}
    tokens = TokenUsage()
    output_failures = 0
    with result_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row or row[0].strip().upper() in {"ANSWER", "回答"}:
                continue
            parsed = parse_result_row(row)
            tokens += parsed.tokens
            if parsed.status == "output_failure":
                output_failures += 1
                continue
            predictions[parsed.product_id] = parsed.answer
    return predictions, tokens, output_failures


def compute_metrics(
    gt_products: set[str],
    predictions: dict[str, str],
) -> tuple[int, int, int, float, float, float]:
    tp = sum(
        1
        for product_id, answer in predictions.items()
        if answer == "YES" and product_id in gt_products
    )
    fp = sum(
        1
        for product_id, answer in predictions.items()
        if answer == "YES" and product_id not in gt_products
    )
    fn = sum(
        1
        for product_id in gt_products
        if predictions.get(product_id, "NO") != "YES"
    )

    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    fscore = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    return tp, fp, fn, recall, precision, fscore


def evaluate_question(
    ground_truth: GroundTruth,
    result_dir: Path,
    data_type: str,
) -> QuestionMetrics:
    result_path = find_result_file(result_dir, ground_truth.question_id, data_type)
    predictions, tokens, output_failures = load_predictions(result_path)
    tp, fp, fn, recall, precision, fscore = compute_metrics(
        ground_truth.product_ids,
        predictions,
    )
    return QuestionMetrics(
        question_id=ground_truth.question_id,
        question=ground_truth.question,
        gt_count=len(ground_truth.product_ids),
        output_count=tp + fp,
        tp_count=tp,
        recall=recall,
        precision=precision,
        fscore=fscore,
        tp=tp,
        fp=fp,
        fn=fn,
        tokens=tokens,
        output_failures=output_failures,
    )


def format_metric(value: float) -> str:
    return f"{value:.4f}"


def format_token_summary(tokens: TokenUsage) -> str:
    return (
        f"input_tokens : {tokens.input_tokens} / "
        f"output_tokens : {tokens.output_tokens} / "
        f"reasoning_tokens : {tokens.reasoning_tokens}"
    )


def format_question_row(metrics: QuestionMetrics) -> str:
    return (
        f"{metrics.question_id}\t{metrics.question}\t{metrics.gt_count}\t"
        f"{metrics.output_count}\t{metrics.tp_count}\t"
        f"{format_metric(metrics.recall)}\t"
        f"{format_metric(metrics.precision)}\t{format_metric(metrics.fscore)}\t"
        f"{metrics.tokens.input_tokens}\t{metrics.tokens.output_tokens}\t"
        f"{metrics.tokens.reasoning_tokens}"
    )


def compute_micro_average(all_metrics: list[QuestionMetrics]) -> tuple[float, float, float]:
    tp = sum(item.tp for item in all_metrics)
    fp = sum(item.fp for item in all_metrics)
    fn = sum(item.fn for item in all_metrics)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    fscore = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    return recall, precision, fscore


def compute_macro_average(all_metrics: list[QuestionMetrics]) -> tuple[float, float, float]:
    if not all_metrics:
        return 0.0, 0.0, 0.0
    recall = sum(item.recall for item in all_metrics) / len(all_metrics)
    precision = sum(item.precision for item in all_metrics) / len(all_metrics)
    fscore = sum(item.fscore for item in all_metrics) / len(all_metrics)
    return recall, precision, fscore


def evaluate_all(
    ground_truth_path: Path,
    result_dir: Path,
    data_type: str,
) -> list[QuestionMetrics]:
    ground_truths = load_ground_truth(ground_truth_path)
    metrics = []
    for question_id in sorted(ground_truths):
        metrics.append(
            evaluate_question(ground_truths[question_id], result_dir, data_type)
        )
    return metrics


def print_report(all_metrics: list[QuestionMetrics]) -> None:
    gt_total = sum(item.gt_count for item in all_metrics)
    output_total = sum(item.output_count for item in all_metrics)
    tp_total = sum(item.tp_count for item in all_metrics)
    token_total = TokenUsage()
    output_failure_total = 0
    for item in all_metrics:
        token_total += item.tokens
        output_failure_total += item.output_failures

    for item in all_metrics:
        print(format_question_row(item))

    micro_recall, micro_precision, micro_fscore = compute_micro_average(all_metrics)
    macro_recall, macro_precision, macro_fscore = compute_macro_average(all_metrics)

    print(
        "Micro average\t\t"
        f"{gt_total}\t{output_total}\t{tp_total}\t"
        f"{format_metric(micro_recall)}\t"
        f"{format_metric(micro_precision)}\t"
        f"{format_metric(micro_fscore)}\t\t\t"
    )
    print(
        "Macro average\t\t\t\t\t"
        f"{format_metric(macro_recall)}\t"
        f"{format_metric(macro_precision)}\t"
        f"{format_metric(macro_fscore)}\t\t\t"
    )
    print(f"Total tokens\t\t\t\t\t\t\t\t{format_token_summary(token_total)}")
    print(f"Output Failure\t\t\t\t\t\t\t\t{output_failure_total}")


def main() -> None:
    args = parse_args()
    ground_truth_path = Path(args.file).expanduser().resolve()
    result_dir = Path(args.result_dir).expanduser().resolve()

    if not ground_truth_path.is_file():
        raise SystemExit(f"ground truth file not found: {ground_truth_path}")
    if not result_dir.is_dir():
        raise SystemExit(f"result directory not found: {result_dir}")

    all_metrics = evaluate_all(ground_truth_path, result_dir, args.data_type)
    print_report(all_metrics)


if __name__ == "__main__":
    main()
