import base64
import hashlib
import json
import struct
import sys
from pathlib import Path
from urllib.request import Request, urlopen


image_path = Path("results/plot_pareto.png")
image = image_path.read_bytes()
if image[:8] != b"\x89PNG\r\n\x1a\n":
    raise ValueError(f"not a PNG: {image_path}")
width, height = struct.unpack(">II", image[16:24])
model = sys.argv[1] if len(sys.argv) > 1 else "google/gemini-2.5-flash"
prompt = """Inspect only the attached chart image. Check whether: (1) colored curves are visibly smooth rather than polygonal, (2) every colored curve starts at the black bare diamond and reaches its matching colored × endpoint, (3) curves follow their intended-side Pareto control points before the endpoint, (4) no off-plot downward triangles remain, and (5) no material text/line collision exists. A dominated final endpoint may legitimately backtrack after the Pareto envelope. Report concrete visible defects only. State the displayed chart title and end with your model identity."""
payload = {
    "model": model,
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(image).decode()}},
        ],
    }],
    "temperature": 0,
}
key = json.loads((Path.home() / ".pi/agent/auth.json").read_text())["openrouter"]["key"]
request = Request(
    "https://openrouter.ai/api/v1/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    method="POST",
)
with urlopen(request, timeout=180) as response:
    result = json.load(response)
review = result["choices"][0]["message"]["content"]
print(
    f"IMAGE_SENT path={image_path} bytes={len(image)} dimensions={width}x{height} "
    f"sha256={hashlib.sha256(image).hexdigest()} model={result['model']}"
)
print(review)
print("— PI/OpenAI Codex")
