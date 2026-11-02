"""Keep temporarily hidden papers and their assets out of public releases."""
def visible_papers(records):
    return [r for r in records if r.get('visible', True)]

def visible_assets(records, assets):
    hidden = {r['id'] for r in records if not r.get('visible', True)}
    return [a for a in assets if a.get('paper_id') not in hidden]
