import base64
import json

# Usage: py src/utils/dev_sample_request.py <path_to_file> <pdf|docx|image>
import sys

p = sys.argv[1]
ft = sys.argv[2]

with open(p, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")

print(
    json.dumps(
        {
            "fileName": p.split("\\")[-1],
            "fileType": ft,
            "fileBase64": b64,
        }
    )
)
