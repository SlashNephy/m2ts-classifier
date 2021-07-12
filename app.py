import os
import re
import time
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from pprint import pprint

import Levenshtein

TARGET_EXTENSION = os.getenv("TARGET_EXTENSION", "m2ts")
OUTPUT_DIRECTORY = os.getenv("OUTPUT_DIRECTORY")
MOUNT_POINTS = [v for k, v in os.environ.items() if k.startswith("MOUNT_POINTS")]
LD_THRESHOLD = float(os.getenv("LD_THRESHOLD", "0.5"))
MATCH_THRESHOLD = int(os.getenv("MATCH_THRESHOLD", "4"))
SEQUENCE_THRESHOLD = int(os.getenv("SEQUENCE_THRESHOLD", "4"))
INTERVAL_SECONDS = int(os.getenv("INTERVAL_SECONDS", "900"))
PREFIXES_PATTERN = re.compile(os.getenv("PREFIXES_PATTERN", r"^(アニメ\s|アニメA・|アニメギルド|アニメ26)"))
SUFFIXES_PATTERN = re.compile(os.getenv("SUFFIXES_PATTERN", r"(第\d*|#\d*|\(\d+\)|ほか|[\(「])\s*$"))
BRACKETS_PATTERN = re.compile(os.getenv("BRACKETS_PATTERN", r"(\[.+?\]|【.+?】|「.+?」)"))
SUPPORT_COMSKIP_TVTPLAY = os.getenv("SUPPORT_COMSKIP_TVTPLAY") == "1"

def enumerate_paths():
    return [
        path
        for mp in MOUNT_POINTS
        for path in Path(mp).glob(f"**/*.{TARGET_EXTENSION}")
        if path.is_file() and not path.is_symlink()
    ]

def enumerate_broken_links():
    return [
        path
        for path in Path(OUTPUT_DIRECTORY).glob("**/*")
        if path.is_symlink() and not path.is_file()
    ]

def enumerate_empty_directories():
    return [
        path
        for path in Path(OUTPUT_DIRECTORY).glob("**/*")
        if path.is_dir() and not any(path.iterdir())
    ]

def enumerate_toplevel_links():
    return [
        path
        for path in Path(OUTPUT_DIRECTORY).glob("*")
        if path.is_symlink() and path.is_file()
    ]

def remove_brackets(text):
    return BRACKETS_PATTERN.sub("", text)

def remove_prefix(text):
    return PREFIXES_PATTERN.sub("", text)

def remove_suffix(text):
    return SUFFIXES_PATTERN.sub("", text)


windows_special_characters_pattern = re.compile(r"[<>:\"/\\|\?\*]")
def remove_windows_special_characters(text):
    return windows_special_characters_pattern.sub("", text)


@dataclass(frozen=True)
class Entry:
    path: Path
    name: str

def find_common_sequence(a, b):
    match = SequenceMatcher(None, a, b).find_longest_match(0, len(a), 0, len(b))
    return a[match.a: match.a + match.size]

def find_chapter_path(path):
    chapter_path = path.with_suffix(".chapter")
    if chapter_path.exists():
        return chapter_path

    chapters_dir = path.parent / "chapters"
    if chapters_dir.exists():
        chapter_path = chapters_dir / path.with_suffix(".chapter").name
        if chapter_path.exists():
            return chapter_path

def create_directory(name):
    directory = Path(OUTPUT_DIRECTORY) / name
    if not directory.exists():
        directory.mkdir()

    return directory

def create_link(directory, src):
    link_path = directory / src.name
    if not link_path.is_symlink():
        link_path.symlink_to(src)
        print(f"create symlink: {link_path}")

        if SUPPORT_COMSKIP_TVTPLAY:
            chapter_path = find_chapter_path(src)
            if chapter_path:
                chapters_directory = link_path.parent / "chapters"
                if not chapters_directory.exists():
                    chapters_directory.mkdir()

                chapter_link_path = chapters_directory / link_path.with_suffix(".chapter").name
                chapter_link_path.symlink_to(chapter_path)
                print(f"create symlink: {chapter_link_path}")

def create_links():
    checked_entries = []
    entries = [
        Entry(
            path,
            name=remove_suffix(remove_prefix(remove_windows_special_characters(remove_brackets(unicodedata.normalize("NFKC", path.stem))))).strip()
        )
        for path in enumerate_paths()
    ]
    entries.sort(key=lambda x: x.name)

    for e1 in entries:
        if e1 in checked_entries or not e1.name:
            continue

        print(e1)

        # 編集距離をすべて求める
        lds = {
            e2: Levenshtein.distance(e1.name, e2.name) / max(len(e1.name), len(e2.name))
            for e2 in entries
            if e2.name
        }

        # 条件を満たす編集距離だけを取り出す
        filtered_lds = {
            e2: ld
            for e2, ld in lds.items()
            if ld < LD_THRESHOLD
        }

        pprint(filtered_lds)
        if len(filtered_lds) < MATCH_THRESHOLD:
            continue

        # 共通文字列を探し, 最も最短のものをディレクトリ名とする
        sequences = [
            find_common_sequence(e1.name, e2.name)
            for e2 in filtered_lds.keys()
        ]
        min_sequence = min(sequences, key=lambda x: len(x))
        common_sequence = remove_suffix(remove_prefix(min_sequence)).strip()

        print(common_sequence)
        if len(common_sequence) < SEQUENCE_THRESHOLD:
            continue

        # ディレクトリを作成する
        link_dir = create_directory(common_sequence)

        # シンボリックリンクを作成する
        for e2 in filtered_lds.keys():
            create_link(link_dir, e2.path)

        checked_entries.extend(list(filtered_lds.keys()))

    for e in entries:
        if e not in checked_entries:
            create_link(Path(OUTPUT_DIRECTORY), e.path)

def cleanup_links():
    # 壊れたシンボリックリンクを削除
    for path in enumerate_broken_links():
        path.unlink()
        print(f"remove symlink: {path}")

    # 空のディレクトリを削除
    for directory in enumerate_empty_directories():
        directory.rmdir()
        print(f"remove directory: {directory}")

    # OUTPUT_DIRECTORY のトップレベルから他のフォルダに含まれているリンクを削除
    directories = [x for x in Path(OUTPUT_DIRECTORY).iterdir() if x.is_dir()]
    for path in enumerate_toplevel_links():
        for directory in directories:
            if (directory / path.name).exists():
                path.unlink()
                print(f"remove symlink: {path}")
                break


if __name__ == "__main__":
    if not OUTPUT_DIRECTORY or not MOUNT_POINTS:
        raise RuntimeError("OUTPUT_DIRECTORY or MOUNT_POINTS is not defined.")

    while True:
        create_links()
        cleanup_links()

        time.sleep(INTERVAL_SECONDS)
