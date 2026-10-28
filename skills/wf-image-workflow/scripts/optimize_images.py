#!/usr/bin/env python3
"""
Image Optimization Script for Workforces
Compresses, resizes, and converts images according to workforces/images.json configuration.
Supports WebP/JPEG conversion using Pillow or native system tools (macOS sips fallback).
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Aspect ratio multipliers (Height / Width)
ASPECT_RATIOS = {
    "1:1": 1.0,
    "3:4": 4.0 / 3.0,
    "4:3": 3.0 / 4.0,
    "9:16": 16.0 / 9.0,
    "16:9": 9.0 / 16.0,
    "2:3": 3.0 / 2.0,
    "3:2": 2.0 / 3.0,
}


def load_image_config(config_path: Path) -> dict:
    """Load image specifications from workforces/images.json or fallback paths."""
    if not config_path.exists():
        fallback = config_path.parent / "docs" / "images.json"
        if fallback.exists():
            config_path = fallback
        else:
            return {"images": []}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as err:
        print(f"⚠️ Warning: Could not read image configuration from {config_path}: {err}", file=sys.stderr)
        return {"images": []}


def optimize_with_pillow(input_path: Path, output_path: Path, target_w: int, target_h: int, quality: int, out_format: str):
    """Optimize and resize using Python Pillow library."""
    from PIL import Image

    with Image.open(input_path) as img:
        img = img.convert("RGB")
        if target_w and target_h:
            # Crop to aspect ratio then resize
            img_w, img_h = img.size
            target_aspect = target_w / target_h
            current_aspect = img_w / img_h

            if current_aspect > target_aspect:
                # Image is wider than target -> crop sides
                new_w = int(img_h * target_aspect)
                left = (img_w - new_w) // 2
                img = img.crop((left, 0, left + new_w, img_h))
            else:
                # Image is taller than target -> crop top/bottom
                new_h = int(img_w / target_aspect)
                top = (img_h - new_h) // 2
                img = img.crop((0, top, img_w, top + new_h))

            img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        save_format = "WEBP" if out_format.lower() == "webp" else "JPEG"
        img.save(output_path, format=save_format, quality=quality, optimize=True)


def optimize_with_sips(input_path: Path, output_path: Path, target_w: int, target_h: int):
    """Fallback optimizer using macOS native sips command."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["cp", str(input_path), str(output_path)], check=True)
    cmd = ["sips", "-s", "format", "jpeg"]
    if target_w:
        cmd.extend(["--resampleWidth", str(target_w)])
    if target_h:
        cmd.extend(["--resampleHeight", str(target_h)])
    cmd.append(str(output_path))
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def process_images(input_dir: Path, output_dir: Path, config_file: Path, quality: int, out_format: str):
    """Process and optimize all images in the input directory."""
    if not input_dir.exists():
        print(f"ℹ️ Input directory does not exist: {input_dir}. Nothing to optimize.")
        return 0

    config_data = load_image_config(config_file)
    spec_map = {item.get("slug"): item for item in config_data.get("images", []) if "slug" in item}

    has_pillow = False
    try:
        import PIL
        has_pillow = True
    except ImportError:
        has_pillow = False

    output_dir.mkdir(parents=True, exist_ok=True)
    image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    candidates = [p for p in input_dir.iterdir() if p.suffix.lower() in image_extensions]

    if not candidates:
        print(f"ℹ️ No images found in {input_dir}.")
        return 0

    print(f"🖼️ Found {len(candidates)} image(s) to optimize using {'Pillow' if has_pillow else 'macOS sips'}...\n")
    processed = 0

    for src_path in candidates:
        slug = src_path.stem
        spec = spec_map.get(slug, {})

        target_w = None
        target_h = None

        if "dimensions" in spec and "width" in spec["dimensions"]:
            target_w = int(spec["dimensions"]["width"])
            aspect_str = spec.get("aspectRatio", "16:9")
            ratio = ASPECT_RATIOS.get(aspect_str, 9.0 / 16.0)
            target_h = int(target_w * ratio)

        ext = f".{out_format.lower()}"
        dest_path = output_dir / f"{slug}{ext}"

        orig_size = src_path.stat().st_size
        try:
            if has_pillow:
                optimize_with_pillow(src_path, dest_path, target_w or 1200, target_h or 675, quality, out_format)
            else:
                optimize_with_sips(src_path, dest_path, target_w or 1200, target_h or 675)

            new_size = dest_path.stat().st_size
            savings = max(0.0, ((orig_size - new_size) / orig_size) * 100) if orig_size > 0 else 0
            print(f"  ✓ {slug}{ext} ({orig_size // 1024} KB → {new_size // 1024} KB, -{savings:.1f}%)")
            processed += 1
        except Exception as err:
            print(f"  ❌ Error optimizing {src_path.name}: {err}", file=sys.stderr)

    print(f"\n✨ Completed: Optimized {processed} image(s) to {output_dir}/.")
    return processed


def main():
    parser = argparse.ArgumentParser(description="Workforces Image Optimizer")
    parser.add_argument("--input-dir", default="./public/images_original", help="Directory containing original images")
    parser.add_argument("--output-dir", default="./public/images", help="Target output directory for optimized images")
    parser.add_argument("--config", default="workforces/images.json", help="Path to workforces/images.json")
    parser.add_argument("--quality", type=int, default=82, help="Image quality (1-100, default: 82)")
    parser.add_argument("--format", default="jpg", choices=["jpg", "webp", "jpeg"], help="Output format (jpg or webp)")

    args = parser.parse_args()
    process_images(Path(args.input_dir), Path(args.output_dir), Path(args.config), args.quality, args.format)


if __name__ == "__main__":
    main()
