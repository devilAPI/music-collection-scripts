#!/usr/bin/env python3
"""Crop wide (e.g. 16:9 YouTube thumbnail) cover art in .opus files to 1:1 center square."""

import argparse
import base64
import glob
import io
import os
import sys

from mutagen.oggopus import OggOpus
from mutagen.flac import Picture
from PIL import Image


WIDE_THRESHOLD = 1.2  # width/height ratio above which we consider it "wide"


def get_cover(opus_file):
    if not opus_file.tags or "metadata_block_picture" not in opus_file.tags:
        return None, None
    raw = opus_file.tags["metadata_block_picture"][0]
    pic = Picture(base64.b64decode(raw))
    img = Image.open(io.BytesIO(pic.data))
    return pic, img


def crop_center_square(img):
    w, h = img.size
    new_size = min(w, h)
    left = (w - new_size) // 2
    top = (h - new_size) // 2
    return img.crop((left, top, left + new_size, top + new_size))


def save_cover(opus_file, pic, cropped, path):
    buf = io.BytesIO()
    fmt = "JPEG" if pic.mime == "image/jpeg" else "PNG"
    save_kwargs = {"format": fmt}
    if fmt == "JPEG":
        save_kwargs["quality"] = 95
    cropped.save(buf, **save_kwargs)

    new_pic = Picture()
    new_pic.type = pic.type
    new_pic.mime = pic.mime
    new_pic.desc = pic.desc
    new_pic.width = cropped.width
    new_pic.height = cropped.height
    new_pic.depth = pic.depth
    new_pic.colors = pic.colors
    new_pic.data = buf.getvalue()

    opus_file.tags["metadata_block_picture"] = [
        base64.b64encode(new_pic.write()).decode("ascii")
    ]
    opus_file.save()


def process_file(path, dry_run=False):
    try:
        f = OggOpus(path)
    except Exception as e:
        return "error", f"can't open: {e}"

    try:
        pic, img = get_cover(f)
    except Exception as e:
        return "error", f"corrupt cover: {e}"
    if pic is None:
        return "skip", "no cover"

    ratio = img.width / img.height
    if ratio <= WIDE_THRESHOLD:
        return "skip", f"{img.width}x{img.height} already ok (ratio {ratio:.2f})"

    if dry_run:
        return "would_fix", f"{img.width}x{img.height} -> {img.height}x{img.height}"

    cropped = crop_center_square(img)
    save_cover(f, pic, cropped, path)
    return "fixed", f"{img.width}x{img.height} -> {cropped.width}x{cropped.height}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Directory to scan or single .opus file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report what would be changed, don't modify files",
    )
    args = parser.parse_args()

    if os.path.isfile(args.path):
        files = [args.path]
    else:
        files = sorted(glob.glob(os.path.join(args.path, "**", "*.opus"), recursive=True))

    stats = {"skip": 0, "fixed": 0, "would_fix": 0, "error": 0}

    try:
        for path in files:
            status, msg = process_file(path, dry_run=args.dry_run)
            stats[status] += 1
            if status in ("fixed", "would_fix", "error"):
                label = {"fixed": "FIXED", "would_fix": "WOULD FIX", "error": "ERROR"}[status]
                print(f"[{label}] {path}\n  {msg}")
    except KeyboardInterrupt:
        print("\n\nInterrupted! Last file was fully saved before stopping.")

    print(f"\n--- Summary ---")
    print(f"Total files:  {len(files)}")
    print(f"Skipped:      {stats['skip']}")
    if args.dry_run:
        print(f"Would fix:    {stats['would_fix']}")
    else:
        print(f"Fixed:        {stats['fixed']}")
    print(f"Errors:       {stats['error']}")


if __name__ == "__main__":
    main()
