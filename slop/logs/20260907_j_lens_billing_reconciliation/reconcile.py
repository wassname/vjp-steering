"""PI/OpenAI Codex: replace three identified startup reserves with metered costs."""
import json
from decimal import Decimal as D
from pathlib import Path
p = Path(__file__).parent
text=(p/'september7-hourly.log').read_text()
rows=json.loads(text[text.index('\n')+1:text.rindex('\nEXIT_CODE=')])
reserves={'ap-49QJqvkch6JhN6V9wmw4mE':'5', 'ap-yh5THLF10Dl4TQlTFdJunH':'1', 'ap-f8aD8yg7WT3xhqMTkix9y7':'.75'}
items=[]
for app,reserve in reserves.items():
    rs=[r for r in rows if r['object_id']==app]
    assert {r['resource'] for r in rs}=={'Memory','CPU','H100'}
    cost=sum(D(r['cost']) for r in rs)
    items.append({'app':app,'old_reserve':reserve,'metered_cost':str(cost)})
released=sum(D(r['old_reserve'])-D(r['metered_cost']) for r in items)
late_reserve=D('.25')
available=D('2.01988872744')+released-late_reserve
out={'identified_failures':items,'released_before_late_allowance':str(released),'new_late_adjustment_reserve':str(late_reserve),'available':str(available),'after_proposed_1_20':str(available-D('1.20')),'all_other_reserves':'unchanged','billing_status':'metered snapshot, not final invoice'}
(p/'reconciliation.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
