# AI Generation Reference

**Three backends, in order of preference:**

| Backend | How | Needs | When |
|---|---|---|---|
| **Blender MCP native** | `generate_hunyuan3d_model` / `generate_hyper3d_model_via_text` / `_via_images` | a checkbox in the addon panel | default — nothing to install |
| **Local Hunyuan3D-2** | `hy3dgen` in your own Python | ~25 GB, ideally CUDA | offline work, or full control of the model variant |
| **HF Spaces** | `gradio_client` | network, tolerance for queues | neither of the above is set up |

---

## MCP-Native Backend — preferred

The Blender MCP addon already ships 3D generation. Reach for this before
proposing any install: it needs no Python environment, no weights, and no
gradio client.

**Tencent Hunyuan3D**

```
get_hunyuan3d_status()                       → is the integration on?
generate_hunyuan3d_model(...)               → returns a job
poll_hunyuan_job_status(job_id)     → wait for completion
import_generated_asset_hunyuan(...) → straight into the scene
```

**Hyper3D Rodin** — a second, independent backend:

```
get_hyper3d_status()                    → is the integration on?
generate_hyper3d_model_via_text(...)            → returns a job
poll_rodin_job_status(job_id)  → wait for completion
import_generated_asset(...)    → straight into the scene
```

**Rule 22 applies here too.** Both integrations are OFF in a default install,
and while off the addon does not register their commands — the call answers
`Unknown command type`, not "disabled". Always call `get_hunyuan3d_status()` /
`get_hyper3d_status()` first and show the remediation from the `message` field: the
checkboxes live in the BlenderMCP panel of the 3D Viewport sidebar (press N if
hidden), labelled *Use Tencent Hunyuan 3D model generation* and *Use Hyper3D
Rodin 3D model generation*.

Rule 5 still binds: Rodin and some Hunyuan tiers are credit-based. Confirm with
the user before spending anything, and prefer a free backend when one is set up.

---

## Local Backend — Hunyuan3D-2 Mini

Use this when you want offline generation or a specific model variant. It is a
real install, so say so before proposing it.

### Requirements

- Python 3.10+
- Hunyuan3D-2 repo cloned + `hy3dgen` installed
- Model weights downloaded (~25 GB for all variants)
- Device: CUDA (full pipeline) / MPS (shape only) / CPU (shape only, slow)

### Available Models

| Model | Params | Speed | Quality | Use case |
|---|---|---|---|---|
| `hunyuan3d-dit-v2-mini` | 0.6B | ~16s (CUDA) | Best | Final quality |
| `hunyuan3d-dit-v2-mini-fast` | 0.6B | ~12s (CUDA) | Good | Good balance |
| `hunyuan3d-dit-v2-mini-turbo` | 0.6B | ~8s (CUDA) | Preview | Fast iteration |

On MPS/CPU: expect 3-10x slower than CUDA times above.

### Local API Flow

```python
import torch
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
from hy3dgen.texgen import Hunyuan3DPaintPipeline  # CUDA only

# Auto-detect device
device = 'cuda' if torch.cuda.is_available() else ('mps' if torch.backends.mps.is_available() else 'cpu')

# Step 1: Shape generation (works on all devices)
shape_pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
    '{models_path}/Hunyuan3D-2mini',
    subfolder='hunyuan3d-dit-v2-mini',  # or mini-fast, mini-turbo
    use_safetensors=True,
    device=device
)

mesh = shape_pipeline(image="concept.png")
mesh.export("output_shape.glb")

# Step 2: Texture generation (CUDA only — skip on MPS/CPU)
if device == 'cuda':
    tex_pipeline = Hunyuan3DPaintPipeline.from_pretrained(
        '{models_path}/Hunyuan3D-2mini',
        subfolder='hunyuan3d-paint-v2-mini'
    )
    textured_mesh = tex_pipeline(mesh, image="concept.png")
    textured_mesh.export("output_textured.glb")
else:
    # No texture — proceed to skill TEXTURING phase
    pass
```

### Error Handling (Local)

| Error | Action |
|---|---|
| OOM (out of memory) | Ask user: switch to smaller model (turbo), reduce resolution, or fallback to HF Spaces |
| Model not found | Guide to `/kiln setup` for download |
| MPS not supported op | Fallback to CPU for that operation, warn user about speed |
| Any crash | Ask user: "Switch to HF Spaces for this asset?" — never switch silently |

---

## HF Spaces Backend — Hunyuan3D 2.x

**Check the Space is awake before using it.** A community Space pauses when its
owner stops paying for the GPU. The HTTP endpoint still answers 200, so a browser
or a `curl` of the page tells you nothing — but `gradio_client` refuses outright,
which is the useful signal:

```
ValueError: The current space is in the invalid state: PAUSED.
            Please contact the owner to fix this.
```

That is `Jbowyer/Hunyuan3D-2.1`, the previous default here, measured 2026-08-26.
To check before connecting:

```bash
curl -s https://huggingface.co/api/spaces/<owner>/<name> \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['runtime']['stage'])"
# RUNNING  -> usable
# PAUSED / SLEEPING / BUILD_ERROR -> pick another Space
```

Candidates, measured 2026-08-26:

| Space | Stage | Likes |
|---|---|---:|
| `tencent/Hunyuan3D-2` | RUNNING | 3,370 |
| `Jbowyer/Hunyuan3D-2.1` | **PAUSED** | 62 |

Prefer the vendor's own Space over a community duplicate: a duplicate depends on
one person continuing to pay, which is exactly how the old default died.

**Version drift.** This path was last exercised on 2026-04-01 against
`gradio_client` 1.3.0; PyPI is at 2.6.1 as of 2026-08-26, a major version on.
The Gradio API here is auto-generated, so it can change shape with the Space or
the client. Treat the snippet below as a starting point and print
`client.view_api()` if a call fails, rather than assuming the argument list.

### Setup

- `gradio_client`, installed in a venv:
  `python3 -m venv ~/.hunyuan3d/venv && ~/.hunyuan3d/venv/bin/pip install gradio_client`
  (a bare `pip3 install` fails on any PEP 668 Python — Homebrew, most Linux distros)
- Python 3.10+ recommended

### API — verified signature

Inspected live on `tencent/Hunyuan3D-2`, 2026-08-26, `gradio_client` 2.6.1. The
Space exposes 12 named endpoints; two matter:

| Endpoint | Returns |
|---|---|
| `/shape_generation` | 4 values — mesh `filepath`, `str`, `Dict`, `float` |
| `/generation_all` | 5 values — mesh + textured `filepath`, `str`, `Dict`, `float` |

Both take the **same 13 parameters**, all with defaults, so pass only what you need:

| Parameter | Type | Default |
|---|---|---|
| `caption` | str | None |
| `image` | filepath | None |
| `mv_image_front` / `_back` / `_left` / `_right` | filepath | None |
| `steps` | float | 30 |
| `guidance_scale` | float | 5.0 |
| `seed` | float | 1234 |
| `octree_resolution` | float | 256 |
| `check_box_rembg` | bool | True |
| `num_chunks` | float | 8000 |
| `randomize_seed` | bool | True |

```python
from gradio_client import Client, handle_file

client = Client("tencent/Hunyuan3D-2")        # refuses if the Space is paused

result = client.predict(
    image=handle_file("concept.png"),
    steps=30,
    guidance_scale=5.0,
    octree_resolution=256,
    check_box_rembg=True,
    randomize_seed=False,                      # reproducibility
    seed=1234,
    api_name="/generation_all",                # or /shape_generation for untextured
)
mesh_path = result[0]
```

`randomize_seed` defaults to **True**, which makes runs non-reproducible. Set it
False and fix `seed` when comparing outputs or re-running a batch.

**If a call fails, print the signature rather than guessing** — this API is
auto-generated and changes with the Space:

```python
print(client.view_api(return_format="dict")["named_endpoints"]["/generation_all"])
```

