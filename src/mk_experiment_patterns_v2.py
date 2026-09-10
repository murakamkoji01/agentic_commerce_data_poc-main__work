#!/usr/bin/env python3
"""Create experiment pattern TSV files from questions and directory files.

v2: -f now takes a TSV question file (e.g. Question100Examples_v1.txt) whose
1st column is the question id (e.g. q001) and 3rd column is the question text.

Usage:
    python3 tools/mk_experiment_patterns_v2.py -dir c0 -f Question100Examples_v1.txt --outdir q_c0_0818
"""

import argparse
import re
from pathlib import Path


QUESTION_ID_PATTERN = re.compile(r"^[Qq](\d+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-f", "--file", required=True, help="input question TSV file")
    parser.add_argument(
        "-dir",
        "--dir",
        dest="input_dir",
        required=True,
        help="directory containing target files",
    )
    parser.add_argument(
        "-outdir",
        "--outdir",
        "-out",
        dest="outdir",
        required=True,
        help="output directory",
    )
    return parser.parse_args()


def parse_questions(question_path: Path) -> list[tuple[str, str]]:
    questions = []
    for line in question_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) < 3:
            continue
        match = QUESTION_ID_PATTERN.match(fields[0].strip())
        if not match:
            continue
        number = match.group(1)
        text = fields[2].strip()
        if not text:
            continue
        questions.append((number, text))
    return questions


def list_target_files(input_dir: Path) -> list[Path]:
    files = [path for path in input_dir.rglob("*") if path.is_file()]
    return sorted(files, key=lambda path: str(path))


def output_filename(question_number: str, input_dir: Path) -> str:
    #return f"q_{question_number}_{input_dir.name}_0906.tsv"
    return f"q_{question_number}_{input_dir.name}.tsv"


def write_pattern_file(
    question: str,
    target_files: list[Path],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        f.write("Question\tTarget_file\n")
        for target_file in target_files:
            f.write(f"{question}\t{target_file.resolve()}\n")


def create_pattern_files(
    question_path: Path,
    input_dir: Path,
    outdir: Path,
) -> list[Path]:
    if not question_path.is_file():
        raise FileNotFoundError(f"question file not found: {question_path}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"input directory not found: {input_dir}")

    questions = parse_questions(question_path)
    if not questions:
        raise ValueError(f"no questions found in: {question_path}")

    target_files = list_target_files(input_dir)
    if not target_files:
        raise ValueError(f"no files found in: {input_dir}")

    output_files = []
    for question_number, question in questions:
        output_path = outdir / output_filename(question_number, input_dir)
        write_pattern_file(question, target_files, output_path)
        output_files.append(output_path)
    return output_files


def main() -> None:
    args = parse_args()
    question_path = Path(args.file).expanduser().resolve()
    input_dir = Path(args.input_dir).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()

    output_files = create_pattern_files(question_path, input_dir, outdir)
    print(f"created {len(output_files)} files under {outdir}")


if __name__ == "__main__":
    main()
