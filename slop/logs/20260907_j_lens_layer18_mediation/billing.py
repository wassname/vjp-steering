"""Read-only app status and metered billing, no inference or app creation."""
from decimal import Decimal
import json
from pathlib import Path
import subprocess
root = Path(__file__).parent
app = 'ap-8ppy9NmWu9ueoRBJ6D95We'
commands = {
    'app-status': ['app', 'list', '--json'],
    'billing-report': ['billing', 'report', '--start', '2026-09-07', '--end', '2026-09-09', '--resolution', 'h', '--show-resources', '--json'],
}
results = {}
for name, args in commands.items():
    cmd = ['uv', 'run', '--no-sync', 'modal', *args]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    (root/(name+'.log')).write_text('COMMAND: '+' '.join(cmd)+'\n'+result.stdout+result.stderr+f'\nEXIT_CODE={result.returncode}\n')
    assert result.returncode == 0
    results[name] = json.loads(result.stdout)
status = next(r for r in results['app-status'] if r['app_id'] == app)
assert status['state'] == 'stopped' and status['tasks'] == '0'
resources = [r for r in results['billing-report'] if r['object_id'] == app]
assert resources, 'No metered cost yet; retain allocation'
cost = sum(Decimal(r['cost']) for r in resources)
transport = [json.loads(line) for line in (root/'judge-transport.jsonl').read_text().splitlines()]
assert len(transport) == 18
judge = sum(Decimal(str(r['response']['usage']['cost'])) for r in transport)
summary = {'app': app, 'status': status, 'metered_resources': resources, 'metered_Modal_usd': str(cost),
    'judge_usd': str(judge), 'reported_total_usd': str(cost+judge), 'allocation_usd': '1.50',
    'remaining_within_allocation_usd': str(Decimal('1.50')-cost-judge),
    'unreserved_usd': '5.72509672744', 'allocation_retained': True,
    'metered_not_final_invoice': True, 'automatic_retries': 0}
(root/'budget.json').write_text(json.dumps(summary, indent=2)+'\n')
print('LAYER18_BILLING_PASS', json.dumps(summary))
