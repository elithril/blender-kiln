# Setup — Local Installation Guide

## Model Selection

```
Choose model storage location:
  Default: ~/.hunyuan3d/models/
  Custom:  [enter path]

Available models:
  1. hunyuan3d-dit-v2-mini       (0.6B params, ~6 GB VRAM)  — balanced quality
  2. hunyuan3d-dit-v2-mini-fast  (0.6B params, ~6 GB VRAM)  — faster, slightly lower quality
  3. hunyuan3d-dit-v2-mini-turbo (0.6B params, ~6 GB VRAM)  — fastest, preview quality

Which models to download? (1,2,3 or "all")
```

## Installation Commands (cross-platform)

```bash
# Clone repo
git clone https://github.com/Tencent/Hunyuan3D-2.git {models_path}/Hunyuan3D-2
cd {models_path}/Hunyuan3D-2

# Install dependencies
pip3 install -r requirements.txt
pip3 install -e .

# Download model weights (via huggingface_hub)
python3 -c "
from huggingface_hub import snapshot_download
snapshot_download('tencent/Hunyuan3D-2mini', local_dir='{models_path}/Hunyuan3D-2mini')
"

# (CUDA only) Compile texture generation extensions
# Skip on Mac/no-CUDA — texture will be handled by skill's TEXTURING phase
cd hy3dgen/texgen/custom_rasterizer && python3 setup.py install && cd ../../..
cd hy3dgen/texgen/differentiable_renderer && bash compile_mesh_painter.sh && cd ../../..
```

## Windows-specific Notes

- Use backslash paths or forward slashes in Python
- May need Visual Studio Build Tools for CUDA extension compilation
- `bash compile_mesh_painter.sh` → use Git Bash or WSL

## Post-install Validation

```python
python3 -c "
import torch
from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
device = 'cuda' if torch.cuda.is_available() else ('mps' if torch.backends.mps.is_available() else 'cpu')
print(f'Device: {device}')
pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
    '{models_path}/Hunyuan3D-2mini',
    subfolder='hunyuan3d-dit-v2-mini-turbo',
    use_safetensors=True,
    device=device
)
print('✅ Shape generation ready')
"
```

**If validation passes:** "✅ Local backend ready. Shape generation on {device}."
**If CUDA not available:** "⚠️ No NVIDIA GPU detected. Shape generation will use {mps/cpu} (slower). Texture generation unavailable locally — skill will texture via Blender (phase TEXTURING)."
