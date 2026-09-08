"""Lossless deterministic publication of full logits; never drops generation fields."""
import gzip
import hashlib
import json
from pathlib import Path
root = Path(__file__).parent
raw = root/'generation.json'
compressed = root/'generation.json.gz'
source = raw.read_bytes()
assert not compressed.exists(), 'Do not overwrite published evidence'
packed = gzip.compress(source, mtime=0)
compressed.write_bytes(packed)
assert gzip.decompress(compressed.read_bytes()) == source
result = {'raw_path': str(raw), 'published_path': str(compressed), 'raw_bytes': len(source),
    'gzip_bytes': len(packed), 'raw_sha256': hashlib.sha256(source).hexdigest(),
    'gzip_sha256': hashlib.sha256(packed).hexdigest(), 'decompressed_bytes_exact': True, 'mtime': 0}
(root/'publication.json').write_text(json.dumps(result, indent=2)+'\n')
print('LOSSLESS_GENERATION_PUBLICATION_PASS', json.dumps(result))
