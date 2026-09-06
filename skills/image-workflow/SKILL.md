---
name: image-workflow
description: Manages the visual asset pipeline, including prompt engineering, queue management (`workforces/images.json`), Antigravity image generation, and compression (WebP/JPEG optimization). Reach for this skill when planning marketing or UI imagery, deconstructing reference visuals into reproducible JSON prompts, generating brand assets, or resizing and compressing web assets for optimal page speed.
---
# 🎨 Image Planning & Generation Workflow

The centralized system for defining, prompting, generating, optimizing visual assets across web properties, and deconstructing reference images into structured JSON duplication prompts.

---

## 🗂 File Structure & Boundaries

```
workforces/
└── images.json                          ← Image queue & brand variables (Workspace layer)

skills/image-workflow/
├── SKILL.md                             ← Workflow instructions & schema definitions
├── templates/
│   └── json-image-duplicate-template.json ← Master JSON Image Duplicate prompt template
└── scripts/
    └── optimize_images.py               ← WebP/JPEG compression utility

docs/
└── brand-context.md                     ← Human-facing brand guidelines (Source of truth for variables)

public/
├── images/                              ← Optimized production images used in code (/images/{slug}.jpg or .webp)
└── images_original/                     ← High-res raw generated images
```

---

## 🍌 JSON Image Duplicate Prompt Protocol (Vision → JSON → Nano Banana / Generative Tools)

When a user provides a reference image, UI screenshot, or ad graphic to replicate, use the **JSON Image Duplicate Prompt** extraction protocol.

### 1. Vision Deconstructor Agent / Gem Instructions

```markdown
I need you to create a JSON prompt for me. The prompt will describe the visual aesthetic, style, and elements in the attached image. Make sure it is detailed and accurate enough that it would almost perfectly replicate the image.

Important: Key elements such as text or specific imagery should be clearly labelled at the top of the JSON so that users can modify the prompt without having to search through the code
```

### 2. Output Schema Specification (`json-image-duplicate-template.json`)

All duplicate prompts MUST strictly structure key variables at the very top of the JSON under `editable_elements` so any human or automated process can customize headline text, colors, or core subjects without parsing through deep rendering properties:

```json
{
  "editable_elements": {
    "primary_subject": "A sleek ergonomic mechanical keyboard sitting on a dark oak desk",
    "text_overlays": [
      {
        "text": "WORKSPACES",
        "position": "top-center",
        "font_family": "Clean bold sans-serif",
        "color": "#FFFFFF",
        "styling": "all-caps, subtle drop shadow"
      }
    ],
    "brand_colors": {
      "accent_primary": "#6366F1",
      "accent_secondary": "#EC4899",
      "background_base": "#0F172A"
    },
    "key_props_and_objects": [
      "matte ceramic coffee mug on the right",
      "monstera plant leaf framing the top-left edge",
      "soft ambient lightbar behind monitor"
    ]
  },
  "visual_aesthetic": {
    "style": "High-end commercial tech editorial photography",
    "art_medium": "Photorealistic 3D render / studio photography",
    "mood_and_tone": "Minimalist, focused, premium, moody atmosphere",
    "color_grading": {
      "palette_type": "Deep slate dark mode with vibrant neon accent rim light",
      "contrast": "High dynamic range with deep blacks and sharp highlights",
      "saturation": "Muted base with saturated focal accents"
    }
  },
  "composition_and_framing": {
    "camera_angle": "Elevated 45-degree isometric perspective",
    "framing": "Medium close-up shot",
    "focal_point": "Center keyboard layout and subtle keycap glow",
    "depth_of_field": "Shallow depth of field (f/2.8), soft bokeh on background elements",
    "aspect_ratio": "16:9"
  },
  "lighting_and_environment": {
    "key_light": "Soft diffused top-down key light with warm 4500K color temperature",
    "fill_light": "Subtle cool ambient fill light (#6366F1 tint)",
    "rim_light": "Sharp magenta (#EC4899) edge backlight highlighting object contours",
    "shadows": "Soft contact shadows directly beneath foreground objects"
  },
  "textures_and_materials": {
    "surfaces": [
      "Fine matte anodized aluminum chassis",
      "Natural textured grain dark oak wood surface",
      "Frosted translucent polycarbonate keycaps"
    ],
    "environmental_effects": "Clean air, zero dust, subtle ambient glass reflections"
  },
  "rendering_parameters": {
    "engine_target": "Nano Banana / Flux 1.1 Pro / Midjourney v6 / Imagen 3",
    "quality": "8k resolution, ray-traced reflections, highly detailed subsurface scattering",
    "negative_prompt": "blurry, low resolution, warped text, cartoonish, oversaturated, messy desk, artifacts"
  }
}
```

### 3. Tool Pipeline Execution (Nano Banana & Antigravity)

1. **Ingest Reference**: Analyze reference image or pasted mockup using vision.
2. **Generate JSON**: Produce the standardized JSON duplicate prompt with `editable_elements` clearly exposed at the top.
3. **Customize Variables**: Modify `text_overlays`, `brand_colors`, or `primary_subject` to fit the specific project brand context.
4. **Feed into Image Tool**:
   - For **Nano Banana / External CLI Tools**: Pass the compiled JSON payload or prompt string into the generation tool.
   - For **Antigravity Native Pipeline**: Compile the JSON into a descriptive prompt and invoke `generate_image`.

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
