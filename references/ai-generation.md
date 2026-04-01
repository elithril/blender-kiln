# AI Generation Reference

## HuggingFace Spaces — Hunyuan3D 2.x

Default Space: `Jbowyer/Hunyuan3D-2.1` (community duplicate, GPU L40S)
Tested: 2026-04-01, gradio_client 1.3.0
Note: Gradio API is auto-generated — can break without notice on Space updates.

### Setup

- `pip3 install gradio_client`
- Python 3.10+ recommended

### API Flow (2-step)

Step 1: **Shape generation** (`/shape_generation`) — generates white mesh from image
Step 2: **Export** (`/on_export_click`) — exports with optional texture + face reduction

```python
from gradio_client import Client, handle_file

# Connect to Space
client = Client("Jbowyer/Hunyuan3D-2.1")

# Step 1: Shape generation
result = client.predict(
    image=handle_file("path/to/image.png"),
    mv_image_front=None,
    mv_image_back=None,
    mv_image_left=None,
    mv_image_right=None,
    steps=30,
    guidance_scale=5.5,
    seed=1234,
    octree_resolution=256,
    check_box_rembg=True,
    num_chunks=200000,
    randomize_seed=True,
    api_name="/shape_generation",
)

# result[0] = GLB path (dict with 'value' key)
# result[2] = mesh_stats
glb_path = result[0]["value"]
mesh_stats = result[2]

# Step 2: Export with optional texture + face reduction
export = client.predict(
    mesh_output=handle_file(glb_path),
    file_type="glb",
    reduce_face=True,
    export_texture=True,
    target_face_num=10000,
    api_name="/on_export_click",
)

# export[1] = final GLB path (dict with 'value' key)
final_glb = export[1]["value"]
```

### Generation Modes

| Mode     | Steps | Time  | Use case                  |
| -------- | ----- | ----- | ------------------------- |
| Turbo    | ~10   | ~8s   | Fast iteration, previews  |
| Fast     | ~20   | ~12s  | Good balance              |
| Standard | ~30   | ~16s  | Final quality             |

Default: **Standard**. Suggest **Turbo** for iteration, **Standard** for final.

### Octree Resolution

| Level    | Value | Notes           |
| -------- | ----- | --------------- |
| Low      | 128   | Fastest         |
| Standard | 256   | Default         |
| High     | 512   | Most detail     |

### target_face_num Mapping

| Tier        | Type | target_face_num |
| ----------- | ---- | --------------- |
| lightweight | prop | 900             |
| balanced    | prop | 3250            |
| detailed    | prop | 10000           |
| lightweight | hero | 5500            |
| balanced    | hero | 14000           |
| detailed    | hero | 50000           |
| custom      | —    | user-specified  |

### Error Handling

| Error                        | Skill Behavior                                          |
| ---------------------------- | ------------------------------------------------------- |
| Timeout >300s                | Inform user, offer to wait or cancel                    |
| Queue                        | Show position if available                              |
| Space paused/down            | Show link, offer URL change                             |
| tex_pipeline not defined     | Export without texture, proceed to TEXTURING phase       |
| Mesh degenerate (0 faces)   | Offer retry with different seed or approach change       |
| API schema mismatch          | Inform user, show Space URL                             |

### Concept Art Generation

Three input modes — ask user which they prefer:

#### 1. Text prompt → Pollinations API (default, free, no key)

```bash
curl -s -o "{output_folder}/{asset_name}_concept.png" \
  "https://image.pollinations.ai/prompt/{url_encoded_prompt}?width=1024&height=1024&model=flux&nologo=true&seed={seed}"
```

- Free, no API key required
- Model: FLUX (via Pollinations)
- Rate limit: ~1 request per 10s, retry on HTTP 429
- To iterate: change the prompt or seed, re-run curl
- Output: PNG 1024x1024

#### 2. User-provided image (path or drag-and-drop)

- User provides a local file path (e.g. `/path/to/concept.png`)
- Skip generation entirely, pass directly to Hunyuan3D
- Validate: file exists, is PNG/JPG/WEBP, readable

#### 3. User-provided image URL

- Download via `curl -s -o "{output_folder}/{asset_name}_concept.png" "{url}"`
- Then treat as local image (mode 2)

#### 4. nano-banana MCP (optional, if configured)

If nano-banana MCP is available and user prefers it:
- `generate_image(prompt)` — new image from text
- `continue_editing(prompt)` — iterate on last image
- `edit_image(imagePath, prompt)` — modify existing image
- `get_last_image_info()` — get file path of last image

Note: requires Gemini API key with billing enabled (free tier has 0 quota for image generation models).

#### Prompt rules (all modes)

- Object only, transparent/white background, studio lighting
- Never environment/ground/context
- Character + rigging → T-pose prompt: `"character in T-pose, arms extended horizontally, palms facing down, legs slightly apart, neutral face, white background"`
- Accepted formats: PNG (recommended), JPG, WEBP
- Recommended resolution: 1024x1024 minimum

### Image Requirements for Hunyuan3D

- Transparent or white background (rembg removes it automatically via `check_box_rembg=True`)
- Single object, well-lit, clear silhouette
- Front 3/4 view gives best results for single-view
- Multi-view: only if user provides their own coherent multi-angle images
