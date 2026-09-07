"""PI/OpenAI Codex: read-only Modal billing queries; creates no app."""
import subprocess
from pathlib import Path
root = Path(__file__).parent
commands = {
    'rates': ['rates', '--json'],
    'september-summary': ['summary', '--for', '2026-09', '--json'],
    'september7-hourly': ['report', '--start', '2026-09-07', '--end', '2026-09-08', '--resolution', 'h', '--show-resources', '--json'],
}
for name, args in commands.items():
    command = ['uv', 'run', '--no-sync', 'modal', 'billing', *args]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    text = 'COMMAND: ' + ' '.join(command) + '\n' + result.stdout + result.stderr + f'\nEXIT_CODE={result.returncode}\n'
    (root / (name + '.log')).write_text(text)
    print(text, flush=True)
