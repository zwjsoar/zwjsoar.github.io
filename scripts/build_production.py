#!/usr/bin/env python3
"""Build locally in an isolated allowlisted staging directory. Never deploys."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse,json,os,shutil,subprocess,hashlib
from pdf_assets import paper_pdf_targets,document_pdf_targets
S=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--test-base-url',help='Reserved .invalid fixture URL, for local QA only')
 parser.add_argument('--label',default='production',choices=['production','qa-root','qa-subpath'])
 parser.add_argument('--release',action='store_true',help='Also require explicit local publication approval settings')
 args=parser.parse_args();config=json.loads((S/'data/deployment.json').read_text())
 fixture=bool(args.test_base_url);url=args.test_base_url or config.get('site_url')
 if not url:raise SystemExit('No site_url selected. Leave it unset until the owner chooses the public domain.')
 u=urlsplit(url)
 if u.scheme!='https' or not u.hostname or u.query or u.fragment or u.username or u.password or u.port or '%' in u.path or '..' in u.path.split('/') or '//' in u.path:raise SystemExit('Use an HTTPS site URL without credentials, query, port or ambiguous path.')
 if fixture and not u.hostname.endswith('.invalid'):raise SystemExit('Test builds require a reserved .invalid hostname, never a real domain.')
 if not fixture and (u.hostname.endswith('.invalid') or not config['content_review_complete']):raise SystemExit('Production content review is incomplete (or URL is a fixture). See the consolidated decisions before approval.')
 if args.release and (fixture or not config['publication_enabled'] or not config['github_owner'] or not config['repository']):raise SystemExit('Release disabled: explicit publication approval and GitHub identity settings are required.')
 if args.release and os.environ.get('GITHUB_REPOSITORY') and os.environ['GITHUB_REPOSITORY'].casefold()!=(config['github_owner']+'/'+config['repository']).casefold():raise SystemExit('GitHub repository differs from the approved deployment identity.')
 base=url.rstrip('/')+'/'
 stage=S/'.build'/args.label
 if stage.exists():shutil.rmtree(stage)
 stage.mkdir(parents=True)
 # Copy source code/config and public-content data only; never copy the project parent.
 for name in ['_quarto.yml','_quarto-preview.yml','_quarto-production.yml','robots.txt']:
  shutil.copy2(S/name,stage/name)
 for name in ['scripts','styles','data','_includes']:
  shutil.copytree(S/name,stage/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 assets=json.loads((S/'data/assets.json').read_text())
 papers=json.loads((S/'data/papers.json').read_text())
 approved_pdfs=paper_pdf_targets(papers,assets)|document_pdf_targets(assets)
 for asset in assets:
  rel=Path(asset['target']);src=S/rel
  if (not str(rel).startswith('assets/') and str(rel) not in approved_pdfs) or '..' in rel.parts or src.is_symlink():raise SystemExit('Unsafe public asset path')
  if rel.suffix.lower()=='.pdf' and str(rel)!='assets/cv/CV_WenjunZhu.pdf' and str(rel) not in approved_pdfs:raise SystemExit('Unmapped paper PDF excluded')
  if hashlib.sha256(src.read_bytes()).hexdigest()!=asset['sha256']:raise SystemExit('Selected asset hash changed: '+str(rel))
  dest=stage/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
 # JSON is valid YAML; this override exists only in the temporary checkout.
 profile={'project':{'output-dir':'_site-production','post-render':'python3 scripts/finalize_production.py'},'website':{'site-url':base,'page-footer':{'left':'Wenjun Zhu','center':[{'href':'news/index.qmd','text':'News'}],'right':''}}}
 (stage/'_quarto-production.yml').write_text(json.dumps(profile,ensure_ascii=False,indent=2))
 env=dict(os.environ,ACADEMIC_STAGED_BUILD='1',ACADEMIC_SITE_URL=base,ACADEMIC_TEST_BUILD='1' if fixture else '0')
 subprocess.run(['quarto','render','--profile','production'],cwd=stage,env=env,check=True)
 output=stage/'_site-production'
 subprocess.run([os.sys.executable,str(S/'scripts/validate.py'),'--output',str(output),'--base-url',base],check=True)
 manifest={'profile':'production','fixture':fixture,'site_url':base,'release_settings_checked':args.release,'publication_performed':False,'output':str(output.relative_to(S))}
 (stage/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
