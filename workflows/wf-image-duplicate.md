---
description: Deconstructs a reference image into a high-fidelity JSON Image Duplicate Prompt with editable elements at top, ready for Nano Banana or generative diffusion tools.
---

# Workflow: `/wf-image-duplicate` (JSON Image Duplicate Prompt)

Deconstructs any pasted or referenced image into a precise, production-ready JSON prompt specification formatted for **Nano Banana**, **Flux**, **Midjourney**, **Imagen 3**, or **Antigravity `generate_image`**.

---

## 🎯 Core Directive

Whenever an image is provided for duplication or reverse-prompting, the agent MUST output a structured JSON specification following the [image-workflow](../skills/image-workflow/SKILL.md) schema.

**Key Rule**: All user-customizable fields (`editable_elements` — headline text overlays, brand accent colors, primary subject, key props) MUST be placed at the very top of the JSON payload so they can be modified quickly without searching through rendering attributes.

---

## 🚀 Execution Steps

### Step 1: Vision Ingestion & Deconstruction
Analyze the visual asset across:
1. **Core Subject & Props**: Foreground subjects, contextual props, and bounding relationships.
2. **Text & Typography**: Exact wording, font style, placement, contrast, and treatment.
3. **Lighting & Shadows**: Key light angle, color temperature, fill light tint, rim light contrast, contact shadows.
4. **Color Palette & Grading**: Base surfaces, vibrant accent colors, dynamic range, saturation.
5. **Camera & Framing**: Perspective (isometric, eye-level, heroic), depth of field (f-stop / bokeh), aspect ratio.
6. **Textures & Materials**: Surface finishes (matte aluminum, frosted glassmorphism, oak wood grain).

---

### Step 2: Generate Structured JSON

Format the output strictly according to `../skills/image-workflow/templates/json-image-duplicate-template.json`:

```json
{
  "editable_elements": {
    "primary_subject": "[Main subject description]",
    "text_overlays": [
      {
        "text": "[EXACT TEXT]",
        "position": "top-center | center | bottom-third",
        "font_family": "[Font style]",
        "color": "#HEX",
        "styling": "[Styling details]"
      }
    ],
    "brand_colors": {
      "accent_primary": "#HEX",
      "accent_secondary": "#HEX",
      "background_base": "#HEX"
    },
    "key_props_and_objects": [
      "[Prop 1]",
      "[Prop 2]"
    ]
  },
  "visual_aesthetic": {
    "style": "[Editorial / 3D Render / Photography]",
    "art_medium": "[Medium]",
    "mood_and_tone": "[Atmosphere]",
    "color_grading": {
      "palette_type": "[Palette details]",
      "contrast": "[Contrast]",
      "saturation": "[Saturation]"
    }
  },
  "composition_and_framing": {
    "camera_angle": "[Angle]",
    "framing": "[Shot type]",
    "focal_point": "[Focus area]",
    "depth_of_field": "[Depth / Bokeh]",
    "aspect_ratio": "16:9 | 1:1 | 4:5"
  },
  "lighting_and_environment": {
    "key_light": "[Key light spec]",
    "fill_light": "[Fill light spec]",
    "rim_light": "[Rim light spec]",
    "shadows": "[Shadow spec]"
  },
  "textures_and_materials": {
    "surfaces": [
      "[Material 1]",
      "[Material 2]"
    ],
    "environmental_effects": "[Atmosphere / reflections]"
  },
  "rendering_parameters": {
    "engine_target": "Nano Banana / Flux / Midjourney / Imagen 3",
    "quality": "8k resolution, ray-traced reflections, highly detailed",
    "negative_prompt": "blurry, low resolution, warped text, cartoonish, oversaturated, artifacts"
  }
}
```

---

### Step 3: Tool Dispatch & Generation (Optional)

- **Nano Banana / External Tools**: Copy or feed the resulting JSON directly into the image generation tool.
- **Antigravity Native Tool**: Queue into `workforces/images.json` and invoke `generate_image`.
