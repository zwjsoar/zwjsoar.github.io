#!/usr/bin/env python3
"""Validate generated public HTML and asset boundaries with the Python standard library."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
from collections import Counter
import argparse,json,re,hashlib,xml.etree.ElementTree as ET
from pdf_assets import paper_pdf_targets,document_pdf_targets
S=Path(__file__).resolve().parents[1]
class Document(HTMLParser):
 def __init__(self,source):
  super().__init__();self.meta={};self.links=[];self.ids=set();self.text=[];self.ld=[];self.h1=[];self.lang=None;self.script=False;self.script_data='';self.in_h1=False;self.feed(source)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='html':self.lang=a.get('lang')
  if a.get('id'):self.ids.add(a['id'])
  if tag=='meta':self.meta.setdefault(a.get('name',''),[]).append(a.get('content',''))
  if tag=='h1':self.in_h1=True
  if tag in ['a','img','script','link']:
   url=a.get('src') if tag in ['img','script'] else a.get('href')
   if url:self.links.append((tag,url,a))
  if tag=='script' and a.get('type')=='application/ld+json':self.script=True;self.script_data=''
 def handle_endtag(self,tag):
  if tag=='h1':self.in_h1=False
  if tag=='script' and self.script:self.ld.append(json.loads(self.script_data));self.script=False
 def handle_data(self,data):
  if self.script:self.script_data+=data
  else:self.text.append(data)
  if self.in_h1:self.h1.append(data)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',default=str(S/'_site'));ap.add_argument('--base-url');args=ap.parse_args()
 O=Path(args.output).resolve();base=args.base_url;prod=bool(base);prefix=urlsplit(base).path.rstrip('/') if prod else '';errors=[]
 def check(ok,msg):
  if not ok:errors.append(msg)
 docs={p:Document(p.read_text()) for p in O.rglob('*.html')}
 check(len(docs)==len(json.loads((S/'data/papers.json').read_text()))+(9 if prod else 10),'HTML page count')
 for path,d in docs.items():
  rel=path.relative_to(O).as_posix();joined=' '.join(d.text)
  check(bool(d.meta.get('description')),'Missing description: '+rel)
  check(d.lang==('zh-Hans' if rel=='zh/index.html' else 'en'),'Language: '+rel)
  robots=d.meta.get('robots',[])
  check(robots==(['index, follow'] if prod else ['noindex, nofollow']),'Robots policy: '+rel)
  canonical=[u for tag,u,a in d.links if tag=='link' and a.get('rel')=='canonical']
  check(canonical==([base+rel.removesuffix('index.html')] if prod else []),'Canonical: '+rel)
  for tag,u,a in d.links:
   check('opportunities/' not in u and '1P7AK6pOFBGAo-fOzwXAAdDX_GewEmDKw' not in u,'Retired link: '+rel)
   if prod:check('/review/' not in u,'Review link in production: '+rel)
   parts=urlsplit(u)
   if parts.scheme or parts.netloc:
    if not(prod and parts.scheme==urlsplit(base).scheme and parts.netloc==urlsplit(base).netloc):continue
   if not parts.path:dest=path
   elif parts.path.startswith('/'):
    local=unquote(parts.path)
    if prefix:
     check(local==prefix or local.startswith(prefix+'/'),'Escaped base path: '+u)
     local=local[len(prefix):]
    dest=O/local.lstrip('/')
   else:dest=path.parent/unquote(parts.path)
   if parts.path.endswith('/') or dest.is_dir():dest=dest/'index.html'
   dest=dest.resolve()
   check(dest.is_relative_to(O) and dest.exists(),'Broken local resource: '+rel+' -> '+u)
   if parts.fragment and dest in docs:check(unquote(parts.fragment) in docs[dest].ids,'Broken fragment: '+rel+' -> '+u)
  if prod:check('Local preview' not in joined,'Preview footer leaked: '+rel)
 papers=json.loads((S/'data/papers.json').read_text());normalize=lambda x:re.sub(r'\s+','',x)
 for r in papers:
  p=O/'papers'/r['slug']/'index.html';d=docs[p];txt=normalize(''.join(d.text));m=r['metadata']
  for block in r['body']:check(normalize(block['text']) in txt,'Original text lost: '+r['id'])
  check('source-citation-heading' not in p.read_text() and 'Original website citation' not in ' '.join(d.text),'Duplicate citation block: '+r['id'])
  if not prod:check(normalize(r['citation']['text']) in normalize(''.join(docs[O/'review/index.html'].text)),'Original citation archive lost: '+r['id'])
  for tag,url,attrs in Document(r['citation']['html']).links:
   if tag=='a':check(any(t=='a' and u==url for t,u,a in d.links),'Original public resource lost: '+r['id']+' -> '+url)
  work=d.ld[0];check(work['@type']==r['schema_type'],'Classification: '+r['id'])
  check(r['publication_kind'] in ' '.join(d.text),'Visible classification: '+r['id'])
  if prod:check(work.get('url')==base+'papers/'+r['slug']+'/' and work.get('@id')==base+'papers/'+r['slug']+'/#work','Work identity URL: '+r['id'])
  if r.get('public_pdf') and prod:
   check(d.meta.get('citation_pdf_url')==[base+r['public_pdf']],'Approved PDF metadata: '+r['id'])
   check(work.get('encoding',{}).get('contentUrl')==base+r['public_pdf'],'Approved PDF schema URL: '+r['id'])
  else:check(not d.meta.get('citation_pdf_url'),'Private/unconfigured PDF metadata: '+r['id'])
  if r['collection']!='other':
   abstract='\n\n'.join(b['text'] for b in r['body'] if b['source_block'] in r['abstract_source_blocks'])
   check(work.get('abstract')==abstract,'Abstract mismatch: '+r['id'])
   check(d.meta.get('citation_author')==m['authors'],'Highwire author order: '+r['id'])
   check([a['name'] for a in work['author']]==m['authors'],'Schema author order: '+r['id'])
   if r.get('publication_status')=='conditionally_accepted' or r['collection']=='conditional':
    check(not d.meta.get('citation_publication_date') and not d.meta.get('citation_journal_title') and not d.meta.get('citation_doi'),'Conditional manuscript must not imply final publication: '+r['id'])
    check(work.get('creativeWorkStatus')=='Conditionally accepted' and 'datePublished' not in work and 'isPartOf' not in work,'Conditional manuscript status/date: '+r['id'])
   else:check(d.meta.get('citation_publication_date')==[m.get('publication_date',m['publication_year'])],'Date: '+r['id'])
   check(d.meta.get('citation_title')==[''.join(d.h1).strip()],'Title identity: '+r['id'])
  if r['collection']=='refereed' and r.get('publication_status')!='conditionally_accepted':
   check(d.meta.get('citation_doi')==[m['doi']],'DOI: '+r['id'])
   check(work['identifier']['value']==m['doi'],'Schema DOI: '+r['id'])
   for key,tag in [('journal_title','citation_journal_title'),('book_title','citation_book_title'),('volume','citation_volume'),('issue','citation_issue'),('article_number','citation_article_number')]:
    if m.get(key):check(d.meta.get(tag)==[m[key]],'Field '+tag+': '+r['id'])
   if m.get('article_number'):check(work.get('pagination')==m['article_number'],'Article identifier: '+r['id'])
   elif m.get('page'):
    pages=re.split(r'[-–]',m['page'],maxsplit=1)
    check(d.meta.get('citation_firstpage')==[pages[0]] and work.get('pageStart')==pages[0],'First page: '+r['id'])
    if len(pages)==2:check(d.meta.get('citation_lastpage')==[pages[1]] and work.get('pageEnd')==pages[1],'Last page: '+r['id'])
   check((p.parent/'citation.bib').exists(),'Citation export: '+r['id'])
  listing=docs[O/('working-papers/index.html' if r['collection']=='working' else 'publications/index.html')]
  check(any('/papers/'+r['slug']+'/' in u or 'papers/'+r['slug']+'/' in u for tag,u,a in listing.links),'Paper unreachable from index: '+r['id'])
  listing_source=(O/('working-papers/index.html' if r['collection']=='working' else 'publications/index.html')).read_text()
  article=re.search(r'<article\b[^>]*data-paper-id="'+r['id']+r'".*?</article>',listing_source,re.S)
  check(bool(article),'Missing listing entry: '+r['id'])
  if article:
   entry=Document(article[0]);visible=normalize(''.join(entry.text))
   check(visible.count(normalize(r['title']))==1,'Repeated listing title: '+r['id'])
   for field in ['authors','publication','notes']:
    check(normalize(r['display'][field]) in visible,'Listing field lost: '+r['id']+' '+field)
   topic_config=json.loads((S/'data/publication_topics.json').read_text())
   topic_labels=topic_config['topics']
   check(bool(r['topics']) and set(r['topics'])<=set(t['id'] for t in topic_labels),'Research topics: '+r['id'])
   for link in r['display']['links']:
    if link.get('url'):check(any(t=='a' and (u==link['url'] or link['url'].startswith('/') and urlsplit(u).path.endswith(link['url'])) for t,u,a in entry.links),'Index resource lost: '+r['id'])
    else:check(link['label'] in ''.join(entry.text),'Pending resource label lost: '+r['id'])
 publication_source=(O/'publications/index.html').read_text()
 check('publication-query' in docs[O/'publications/index.html'].ids and 'data-topic="all"' in publication_source,'Publication search/filter controls')
 working_source=(O/'working-papers/index.html').read_text()
 check('publication-query' in docs[O/'working-papers/index.html'].ids and 'data-topic="all"' in working_source,'Working-paper search/filter controls')
 check('working_paper_topics' not in json.loads((S/'data/publication_topics.json').read_text()),'Separate working-paper topic registry returned')
 for topic in topic_config['topics']:
  check('data-topic="'+topic['id']+'"' in publication_source and 'data-topic="'+topic['id']+'"' in working_source,'Shared category control missing: '+topic['id'])
 check('paper-index-intro' not in publication_source,'Removed publication intro returned')
 # Index order and all original non-paper page prose.
 for coll,file in [('refereed','publications/index.html'),('other','publications/index.html'),('working','working-papers/index.html')]:
  source=(O/file).read_text();positions=[source.find('data-paper-id="'+r['id']+'"') for r in papers if r['collection']==coll]
  check(all(x>=0 for x in positions) and positions==sorted(positions),'Citation order: '+coll)
 pages=json.loads((S/'data/pages.json').read_text());mapping={'home':'index.html','about':'cv/index.html','research':'research/index.html','teaching':'teaching/index.html','miscellaneous':'miscellaneous/index.html'}
 for slug,file in mapping.items():
  txt=normalize(''.join(docs[O/file].text))
  profile=json.loads((S/'data/academic_profile.json').read_text())
  replaced=profile['approved_replacement_blocks'].get(slug,[])
  removed=profile.get('approved_removed_blocks',{}).get(slug,[])
  for b in pages[slug]['blocks']:
   if b['source_block'] not in replaced+removed:check(normalize(profile.get('approved_source_text_overrides',{}).get(slug,{}).get(str(b['source_block']),b['text'])) in txt,'English source block missing: '+slug)
  for index in removed:check('data-source-page="'+slug+'" data-source-block="'+str(index)+'"' not in (O/file).read_text(),'Owner-removed block returned: '+slug+' '+str(index))
  revised=(profile['about_paragraphs']+profile['roles']) if slug=='home' else ([profile['research_intro']]+[a['title']+'. '+a['text'] for a in profile['research_areas']]+[g['display'] for g in profile['additional_grants']]) if slug=='research' else []
  for paragraph in revised:check(normalize(paragraph) in txt,'Approved profile content missing: '+slug)
 news=json.loads((S/'data/news.json').read_text())
 for rel in ['index.html','news/index.html']:
  txt=normalize(''.join(docs[O/rel].text))
  for entry in news['entries']:
   if entry.get('visible',True):check(normalize(entry['text']) in txt,'News missing: '+entry['id'])
 asset_records=json.loads((S/'data/assets.json').read_text())
 allow={a['target']:a['sha256'] for a in asset_records}
 approved_pdfs={'assets/cv/CV_WenjunZhu.pdf'}|paper_pdf_targets(papers,asset_records)|document_pdf_targets(asset_records)
 for p in O.rglob('*'):
  check(not p.is_symlink(),'Symlink in artifact: '+str(p))
  if not p.is_file():continue
  rel=p.relative_to(O).as_posix()
  check(not any(x in p.relative_to(O).parts for x in ['materials','planning','scripts','data','.github','.build','.quarto']), 'Private/source directory in artifact: '+rel)
  check(p.suffix not in ['.qmd','.md','.py','.toml','.yaml','.yml'],'Source file in artifact: '+rel)
  if rel.startswith('assets/') or p.suffix.lower()=='.pdf':check(rel in allow and hashlib.sha256(p.read_bytes()).hexdigest()==allow.get(rel),'Unexpected or changed asset: '+rel)
  if p.suffix.lower()=='.pdf':check(rel in approved_pdfs,'Unapproved PDF in artifact: '+rel)
 for rel in allow:check((O/rel).exists(),'Missing asset: '+rel)
 for r in papers:
  if r.get('public_pdf'):
   check(r['public_pdf']=='papers/'+r['slug']+'/paper.pdf','Main PDF must share the abstract directory: '+r['id'])
 check(not (O/'review').exists() if prod else (O/'review/index.html').exists(),'Review page boundary')
 if prod:
  locs=[e.text for e in ET.parse(O/'sitemap.xml').findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
  check(set(locs)=={base+p.relative_to(O).as_posix().removesuffix('index.html') for p in docs},'Sitemap coverage')
  check('Allow: /' in (O/'robots.txt').read_text() and 'Sitemap: '+base+'sitemap.xml' in (O/'robots.txt').read_text(),'Production robots')
  for rel in ['index.html','zh/index.html']:
   d=docs[O/rel];langs={a.get('hreflang'):u for tag,u,a in d.links if a.get('rel')=='alternate' and a.get('hreflang')}
   check(langs=={'en':base,'zh-Hans':base+'zh/','x-default':base},'Reciprocal profile language links')
   person=next(x for x in d.ld if x.get('@type')=='Person');check(person.get('@id')==base+'#person','Shared Person identity')
 else:check('Disallow: /' in (O/'robots.txt').read_text(),'Preview robots')
 report={'profile':'production' if prod else 'preview','base_url':base,'pages_checked':len(docs),'paper_pages_checked':len(papers),'doi_records':sum(bool(r['metadata'].get('doi')) for r in papers),'complete_abstracts':sum(bool(r.get('abstract_source_blocks')) for r in papers),'errors':errors,'passed':not errors,'publication_performed':False}
 (O.parent/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2));raise SystemExit(bool(errors))
if __name__=='__main__':main()
