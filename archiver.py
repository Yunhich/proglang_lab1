#!/usr/bin/env python3
"""
Консольный архиватор / распаковщик
Python 3.14 | stdlib only
Поддержка: zstd, bz2
"""

import argparse
import os
import sys
import time
import tarfile
import bz2
import tempfile
from compression import zstd   # Python 3.14 stdlib

# =========================
# Прогресс-бар
# =========================

def progress_bar(done, total, width=30):
    if total == 0:
        return
    ratio = done / total
    filled = int(width * ratio)
    bar = "#" * filled + "." * (width - filled)
    print(f"\r[{bar}] {ratio*100:5.1f}%", end="")
    if done >= total:
        print()

# =========================
# Сжатие / распаковка
# =========================

def compress_bytes(data: bytes, method: str) -> bytes:
    if method == "zstd":
        return zstd.compress(data)
    elif method == "bz2":
        return bz2.compress(data)
    else:
        raise ValueError("Unknown method")

def decompress_bytes(data: bytes, method: str) -> bytes:
    if method == "zstd":
        return zstd.decompress(data)
    elif method == "bz2":
        return bz2.decompress(data)
    else:
        raise ValueError("Unknown method")

# =========================
# Работа с файлами
# =========================

def compress_file(src, dst, method, benchmark):
    start = time.perf_counter()

    with open(src, "rb") as f:
        data = f.read()

    compressed = compress_bytes(data, method)

    with open(dst, "wb") as f:
        f.write(compressed)

    progress_bar(len(data), len(data))

    if benchmark:
        print(f"Время: {time.perf_counter() - start:.3f} сек")

def decompress_file(src, dst, method, benchmark):
    start = time.perf_counter()

    with open(src, "rb") as f:
        data = f.read()

    raw = decompress_bytes(data, method)

    with open(dst, "wb") as f:
        f.write(raw)

    progress_bar(len(data), len(data))

    if benchmark:
        print(f"Время: {time.perf_counter() - start:.3f} сек")

# =========================
# Директории (через tar)
# =========================

def pack_directory(src_dir, dst_archive, method, benchmark):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".tar") as tmp:
        tar_path = tmp.name

    with tarfile.open(tar_path, "w") as tar:
        tar.add(src_dir, arcname=os.path.basename(src_dir))

    compress_file(tar_path, dst_archive, method, benchmark)
    os.remove(tar_path)

def unpack_directory(src_archive, dst_dir, method, benchmark):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".tar") as tmp:
        tar_path = tmp.name

    decompress_file(src_archive, tar_path, method, benchmark)

    with tarfile.open(tar_path) as tar:
        tar.extractall(dst_dir)

    os.remove(tar_path)

# =========================
# CLI
# =========================

def main():
    parser = argparse.ArgumentParser(
        description="Архиватор / распаковщик (.zst / .bz2)"
    )
    parser.add_argument("src", help="Источник (файл / папка / архив)")
    parser.add_argument("dst", help="Назначение")
    parser.add_argument(
        "-b", "--benchmark",
        action="store_true",
        help="Показать время выполнения"
    )

    args = parser.parse_args()

    src = args.src
    dst = args.dst
    bench = args.benchmark

    if not os.path.exists(src):
        print("Источник не найден")
        sys.exit(1)

    # Определяем режим
    is_unpack = src.endswith((".zst", ".bz2"))

    if is_unpack:
        method = "zstd" if src.endswith(".zst") else "bz2"

        # пробуем как tar
        try:
            os.makedirs(dst, exist_ok=True)
            unpack_directory(src, dst, method, bench)
        except tarfile.ReadError:
            decompress_file(src, dst, method, bench)

    else:
        if not dst.endswith((".zst", ".bz2")):
            print("Для архивации укажите .zst или .bz2")
            sys.exit(1)

        method = "zstd" if dst.endswith(".zst") else "bz2"

        if os.path.isdir(src):
            pack_directory(src, dst, method, bench)
        else:
            compress_file(src, dst, method, bench)

# =========================

if __name__ == "__main__":
    main()
