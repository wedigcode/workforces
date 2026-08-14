---
name: image-workflow
description: End-to-end AI image planning, prompting, generation queue in workforces/images.json, Antigravity generate_image integration, and WebP/JPEG compression.
---

# 🎨 Image Planning & Generation Workflow

The centralized system for defining, prompting, generating, and optimizing visual assets across web properties.

---

## 🗂 File Structure & Boundaries

```
workforces/
└── images.json              ← Image queue & brand variables (Workspace layer)

docs/
└── brand-context.md         ← Human-facing brand guidelines (Source of truth for variables)

public/
├── images/                  ← Optimized production images used in code (/images/{slug}.jpg or .webp)
└── images_original/         ← High-res raw generated images
```

---

## 📋 Queue Schema (`workforces/images.json`)

```json
{
  "brandVariables": {
    "primaryColor": "Deep Slate Blue",
    "primaryHex": "#1E293B",
    "secondaryColor": "Warm Amber",
    "secondaryHex": "#F59E0B",
    "brandMood": "modern, high-trust, technical",
    "visualStyle": "editorial, clean lighting, architectural",
    "tone": "confident and approachable"
  },
  "images": [
    {
      "slug": "hero-dashboard-preview",
      "type": "hero",
      "dimensions": { "width": 1200 },
      "aspectRatio": "16:9",
      "generated": false,
      "outputPath": "public/images/hero-dashboard-preview.jpg",
      "error": null,
      "metadata": {
        "subject": "clean modern SaaS dashboard analytics interface",
        "emotion": "empowering, clear, high-contrast"
      },
      "prompt": "A modern 3D UI perspective of a {{subject}}, glowing ambient lighting in {{primaryColor}}, clean glassmorphism accents, {{brandMood}} atmosphere"
    }
  ]
}
```

---

## ⚡ Generation with Antigravity `generate_image`

Images in the queue are generated via Antigravity's native `generate_image` tool:

1. **Parse pending entries**: Scan `workforces/images.json` for entries where `generated == false`.
2. **Template interpolation**: Replace `{{primaryColor}}`, `{{secondaryColor}}`, `{{brandMood}}`, `{{visualStyle}}` with values from `brandVariables`.
3. **Execute tool call**:
   ```
   generate_image(
     Prompt="...",
     ImageName="hero-dashboard-preview",
     AspectRatio="16:9"
   )
   ```
4. **Mark completed**: Update `generated: true` and save output path.

---

## 🖼️ Image Optimization & Compression

Run the cross-platform optimization tool to compress raw assets for web delivery:

```bash
python3 .agents/skills/image-workflow/scripts/optimize_images.py \
  --input-dir ./public/images_original \
  --output-dir ./public/images \
  --config workforces/images.json \
  --quality 82 \
  --format webp
```

Supports Pillow (PIL) and native macOS `sips` fallback with zero external dependencies.
