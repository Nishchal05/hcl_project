from datetime import date

def _date(value): return date.fromisoformat(value) if value else None
def _applies(d, when, programme, batch):
    start,end=_date(d.get('effective_from')), _date(d.get('effective_to'))
    if start and start > when or end and end < when: return False
    p=d.get('scope_programme','ALL'); b=d.get('scope_batches','')
    if p not in ('ALL','',programme): return False
    # Chroma metadata may contain comma-separated scopes after repeated indexing.
    scopes=[x.strip() for x in b.split(',') if x.strip()]
    plus=[x for x in scopes if x.endswith('+')]
    if plus and batch < min(int(x[:-1]) for x in plus if x[:-1].isdigit()): return False
    return True
def resolve(candidates, relevant_date=None, programme='ALL', batch=9999):
    """Deterministic precedence: applicability, explicit supersession, authority, recency; ties conflict."""
    when=_date(relevant_date) if isinstance(relevant_date,str) else (relevant_date or date.today())
    docs=[dict(x) for x in candidates if _applies(dict(x),when,programme,batch)]
    superseded={x.get('supersedes','').split('#')[0] for x in docs if x.get('supersedes')}
    docs=[x for x in docs if x['doc_id'] not in superseded]
    if not docs: return [], [], 'No applicable authoritative source.'
    best=min(int(x.get('authority_level',99)) for x in docs); docs=[x for x in docs if int(x.get('authority_level',99))==best]
    newest=max(x.get('effective_from') or '0001-01-01' for x in docs); docs=[x for x in docs if (x.get('effective_from') or '0001-01-01')==newest]
    if len(docs)>1: return [], docs, 'Applicable sources have equal authority and effective date.'
    return docs, [], 'Selected by applicability, supersession, authority, and recency.'
