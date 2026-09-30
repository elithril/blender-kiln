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

**State on 2026-09-29, measured by the quality bench** (`bench/`): the Space is
RUNNING, `/shape_generation` works, and **`/generation_all` fails server-side**
with `AppError: 'NameError'` — so there is no free *textured* path here today.
Fall back to `/shape_generation` and texture in Blender (PHASE 5b). Textured
generation on a Mac needs CUDA locally, so a local install does not fix this.

**Version drift.** This path was last exercised on 2026-09-29 against
`gradio_client` 2.7.1.
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
mesh_path = gradio_path(result[0])
```

**`gradio_client` 2.x does not always return a path.** On 2.7.1 the Hunyuan3D
Space returns `result[0]` as a dict (`{"value": path, ...}`) and a copy with
`shutil` fails with `TypeError: ... not dict` — measured. The FLUX Space returns
a plain string. Unwrap both, always:

```python
def gradio_path(x):
    """A file path out of whatever gradio_client handed back."""
    if isinstance(x, dict):
        x = x.get("path") or x.get("value") or x.get("name")
        if isinstance(x, dict):                    # {"value": {"path": ...}}
            return gradio_path(x)
    if not isinstance(x, str):
        raise TypeError(f"no file path in gradio result: {x!r}")
    return x
```

`randomize_seed` defaults to **True**, which makes runs non-reproducible. Set it
False and fix `seed` when comparing outputs or re-running a batch.

**If a call fails, print the signature rather than guessing** — this API is
auto-generated and changes with the Space:

```python
print(client.view_api(return_format="dict")["named_endpoints"]["/generation_all"])
```


---

## Free cloud quota — the real ceiling

Every free Space here runs on **ZeroGPU**, and its quota is per user and per day:
**2 minutes without a Hugging Face account, 3.5 minutes with a free one**,
resetting 24 h after the first use (Hugging Face's own reference,
`huggingface/skills`, `huggingface-zerogpu/references/how-quota-works.md`). One
TRELLIS.2 generation requests 60–120 s: measured on 2026-09-29 on a **free
logged-in account**, the quota ran out after one FLUX image and one Hunyuan3D
shape, with `You have exceeded your free ZeroGPU quota (120s requested vs. 0s left)`.

**`gradio_client` sends the locally saved Hugging Face token by default** (its own
docstring: "the locally saved token is used if there is one"). So whether a
session is anonymous depends on `~/.cache/huggingface/token`, not on the code.
Check it with `hf auth whoami` before quoting a quota.

### Whose account pays the quota — say it, every session

The skill carries no credential and never names an account. Whatever token a
Space call uses is the **current user's own**, from their machine — and
`gradio_client` uses it silently. So, before the first Space call of a session:

1. Run `hf auth whoami` (or `uvx --from huggingface_hub hf auth whoami`).
2. If it names an account, tell the user: "Space calls will count against your
   Hugging Face account `<name>`'s free GPU quota." Offer anonymous calls instead.
3. Anonymous means `Client("<space>", token=False)` — measured: `token=None` (the
   default) sends the saved token, `token=False` sends none. Setting
   `HF_HUB_DISABLE_IMPLICIT_TOKEN=1` does the same for a whole process.

Never read, print, copy or write a token anywhere — not into a script, a log, a
manifest or a message. Needing one means asking the user to run `hf auth login`
themselves.

**A call reserves the Space's declared duration, not the time it runs.** FLUX.1-schnell
produces an image in 5.6 s, yet a call is refused with `90s requested vs. 0s left`;
TRELLIS.2 asks 60–120 s. Budget in reservations, not in seconds of work.

**And the day does not start at midnight.** Measured on a free account: first Space
call on 2026-09-29 at ~15:00, quota spent by ~16:00, and the next morning at 12:45
FLUX was still refused — the reset comes 24 h after the *first* call, so ~15:00.
Plan around it: once the quota is spent, **no Space works for the rest of that
window, concept art included.**

So the free cloud path is **one or two generations a day**. Say so before a batch
of AI assets, never promise it, and never suggest the paid PRO plan (rule 5).

## TRELLIS.2 — candidate, not yet the default

`microsoft/TRELLIS.2` (MIT) outputs a mesh **with baked PBR textures**, which is
exactly what the Hunyuan3D Space's broken `/generation_all` no longer gives. Its
Space API, read live on 2026-09-29 (a generation has NOT completed yet — the
quota above ran out first):

| Endpoint | Takes | Note |
|---|---|---|
| `/start_session` | — | call first; state lives in the client session |
| `/preprocess_image` | `input` | background removal; returns a path |
| `/image_to_3d` | `image`, `seed`, `resolution` ("1024"), sampler settings | |
| `/extract_glb` | `decimation_target`, `texture_size` | **rejects a target under 100,000** — decimate in Blender after (rule 6) |

**Locally on Apple Silicon**, `shivampkumar/trellis-mac` reports ~5 min a model on
an M4 Pro with 24 GB, 18 GB peak, 15 GB of weights — its numbers, not measured
here. **Licences**: TRELLIS.2 is MIT, but that pipeline also pulls **DINOv3**
(Meta's own licence) and **RMBG-2.0 (CC BY-NC 4.0 — non-commercial)**. Say so
before recommending it for anything commercial.

## Concept Art

SKILL.md sends text-prompt concept art here; this section did not exist until the
quality bench found the gap on 2026-09-29.

### Default — FLUX.1-schnell HF Space

Free, no key, **Apache-2.0** (model card, checked 2026-09-29), and it runs through
the same `gradio_client` venv as the 3D Spaces — nothing new to install. Measured:
one 1024×1024 image in **5.6 s**, no watermark.

```python
from gradio_client import Client

client = Client("black-forest-labs/FLUX.1-schnell")
result = client.predict(
    prompt="<asset>, <style>, centered, isolated on a plain white background, "
           "three-quarter view, single object",
    seed=42, randomize_seed=False,               # reproducible
    width=1024, height=1024, num_inference_steps=4,
    api_name="/infer",
)
image_path = gradio_path(result[0])              # a .webp; result[1] is the seed
```

The Space returns **WebP**. Convert before feeding a 3D Space that expects PNG:
`sips -s format png concept.webp --out concept.png` on macOS.

**It does not always obey "no ground".** Measured: grass and a drop shadow under
the subject despite the prompt. Hunyuan3D's `check_box_rembg=True` removes the
background; inspect the result before generating anyway.

Like every ZeroGPU Space it has a per-user quota and can pause. Check
`https://huggingface.co/api/spaces/black-forest-labs/FLUX.1-schnell/runtime`
for `"stage": "RUNNING"` first — a paused Space still answers HTTP 200.

### When the quota is spent

FLUX runs on the same ZeroGPU quota as the 3D Spaces, so a spent quota also means
no concept art. In order of preference, all free:

1. **The user's own image** — a sketch, a photo, a screenshot. Ask for it first.
2. **A CC0 reference from PolyHaven**: every asset has an official preview,
   `thumbnail_url` in `https://api.polyhaven.com/info/<id>` — replace its query
   (`?width=256&height=256&v=…`) with `?width=1024&height=1024`, measured to work —
   transparent PNG, and the real model exists for comparison. Credit it (ToS 2.5).
3. **Scripted modeling from the brief alone**, which needs no image at all.
4. **Wait for the reset** — say when, from the time of the first call.

Never suggest the paid PRO plan to get the quota back (rule 5).

### Not the default any more

| Source | State | Use |
|---|---|---|
| **Pollinations** | **HTTP 402 `Payment-Required` after one free image** (measured 2026-09-29) | Only if it answers 200. On 402, switch source — never pay (rule 5), and never paint over its watermark |
| **nano-banana MCP** | bills a Gemini API key | only on the user's explicit request |
| **mflux** (local FLUX on Apple Silicon, MIT) | not measured here — model size and speed unverified | an offline option to evaluate, not to recommend yet |
