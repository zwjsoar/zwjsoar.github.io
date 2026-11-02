"""Validate the explicit per-paper PDF manifest without reading private sources."""
from pathlib import PurePosixPath
import re

def document_pdf_targets(assets):
    """Allow only explicitly selected archival documents, separate from papers."""
    allowed = set()
    for asset in assets:
        if asset.get('owner_approved_document_pdf') or asset.get('pdf_role') == 'archival_document':
            if (asset['target'] != 'assets/awards/nanyang-awards-2026.pdf'
                    or asset.get('document_id') != 'nanyang-awards-2026'
                    or asset.get('pdf_role') != 'archival_document'
                    or asset.get('owner_approved_document_pdf') is not True
                    or asset.get('paper_id')
                    or not re.fullmatch(r'[0-9a-f]{64}', asset.get('sha256', ''))):
                raise ValueError('Invalid archival PDF: ' + asset['target'])
            allowed.add(asset['target'])
    return allowed

def paper_pdf_targets(papers, assets):
    documents = document_pdf_targets(assets)
    records = {r['id']: r for r in papers}
    if len(records) != len(papers):
        raise ValueError('Duplicate paper ID')
    manifest = {a['target']: a for a in assets}
    if len(manifest) != len(assets):
        raise ValueError('Duplicate asset target')
    main = {}
    for rec in papers:
        target = rec.get('public_pdf')
        if not target:
            continue
        expected = 'papers/' + rec['slug'] + '/paper.pdf'
        asset = manifest.get(target, {})
        if (target != expected or '..' in PurePosixPath(target).parts
                or asset.get('paper_id') != rec['id']
                or asset.get('pdf_role') != 'main'
                or asset.get('owner_approved_paper_pdf') is not True
                or not re.fullmatch(r'[0-9a-f]{64}', asset.get('sha256', ''))):
            raise ValueError('Invalid mapped main PDF: ' + rec['id'])
        main[rec['id']] = target
    allowed = set(main.values())
    for asset in assets:
        target = asset['target']
        path = PurePosixPath(target)
        if path.suffix.lower() != '.pdf' or target == 'assets/cv/CV_WenjunZhu.pdf' or target in documents:
            continue
        if target in allowed:
            continue
        canonical = main.get(asset.get('paper_id'))
        if (not canonical or asset.get('pdf_role') != 'legacy_alias'
                or not target.startswith('assets/papers/') or '..' in path.parts
                or asset.get('owner_approved_paper_pdf') is not True
                or asset.get('alias_of') != canonical
                or asset.get('sha256') != manifest[canonical]['sha256']):
            raise ValueError('Unmapped PDF asset: ' + target)
        allowed.add(target)
    return allowed
