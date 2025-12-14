#!/usr/bin/env python3

import argparse
import os
import sys
import time
import tarfile
import bz2
import tempfile
from compression import zstd

# =========================
# Прогресс-бар
# =========================

def progress_bar(done, total, width=30): // done — сколько выполнено, total — сколько всего, width — ширина полосы
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

def compress_file(src, dst, method, benchmark): // src - путь к файлу, dst - путь к архиву
    start = time.perf_counter()

    with open(src, "rb") as f:
        data = f.read()

    compressed = compress_bytes(data, method)

    with open(dst, "wb") as f:
        f.write(compressed)

    progress_bar(len(data), len(data))

    if benchmark:
        print(f"Время: {time.perf_counter() - start:.3f} сек") // время выполнения

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
    with tempfile.NamedTemporaryFile(delete=False, suffix=".tar") as tmp: // создаём временный файл с расширением tar
        tar_path = tmp.name

    with tarfile.open(tar_path, "w") as tar: // открываем tar, добавляем папку
        tar.add(src_dir, arcname=os.path.basename(src_dir))

    compress_file(tar_path, dst_archive, method, benchmark) // сжимаем tar
    os.remove(tar_path) // удаляем временный tar

def unpack_directory(src_archive, dst_dir, method, benchmark):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".tar") as tmp: // создаём временный файл для tar
        tar_path = tmp.name

    decompress_file(src_archive, tar_path, method, benchmark) // распаковываем zst/bz2 в временный tar

    with tarfile.open(tar_path) as tar: // открываем tar и извлекаем всё в папку dst_dir
        tar.extractall(dst_dir)

    os.remove(tar_path) // удаляем временный tar

# =========================
# CLI
# =========================

def main():
    parser = argparse.ArgumentParser( // парсер аргументов
        description="Архиватор / распаковщик (.zst / .bz2)"
    )
    parser.add_argument("src", help="Источник (файл / папка / архив)") // аргумент 1: что архивируем или какой архив распаковываем
    parser.add_argument("dst", help="Назначение") // аргумент 2: куда сохранить архив / куда распаковать
    parser.add_argument( // ключ --benchmark
        "-b", "--benchmark",
        action="store_true",
        help="Показать время выполнения"
    )

    args = parser.parse_args() // разбираем аргументы из командной строки

    src = args.src
    dst = args.dst
    bench = args.benchmark

    if not os.path.exists(src): // если источник не существует — сообщаем и выходим с кодом ошибки 1
        print("Источник не найден")
        sys.exit(1)

    # Определяем режим
    is_unpack = src.endswith((".zst", ".bz2"))

    if is_unpack: // метод выбираем по расширению архива
        method = "zstd" if src.endswith(".zst") else "bz2"

        # пробуем как tar
        try:
            os.makedirs(dst, exist_ok=True) // создаём папку назначения
            unpack_directory(src, dst, method, bench) // распаковываем в неё tar-содержимое
        except tarfile.ReadError:
            decompress_file(src, dst, method, bench)

    else: // если это не tar, распаковываем как файл
        if not dst.endswith((".zst", ".bz2")):
            print("Для архивации укажите .zst или .bz2")
            sys.exit(1)

        method = "zstd" if dst.endswith(".zst") else "bz2"

        if os.path.isdir(src): // если src - папка: делаем tar и сжимаем
            pack_directory(src, dst, method, bench)
        else: // Если src - файл: сжимаем напрямую
            compress_file(src, dst, method, bench)

# =========================

if __name__ == "__main__":
    main()

