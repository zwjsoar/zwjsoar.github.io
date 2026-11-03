#!/usr/bin/env python3
"""Generate local Quarto pages from editable public-content JSON. Standard library only."""
from pathlib import Path
from html import escape
from html.parser import HTMLParser
from urllib.parse import unquote
import json,re
from scholarly import build_metadata,bibtex
from pdf_assets import paper_pdf_targets
from publication_visibility import visible_papers
from build_context import PRODUCTION,BASE,page_url,person_schema
S=Path(__file__).resolve().parents[1]
def read(name):return json.loads((S/'data'/name).read_text())
PAGES=read('pages.json');ALL_PAPERS=read('papers.json');PAPERS=visible_papers(ALL_PAPERS);NEWS=read('news.json');PERSON=read('person.json')
TOPIC_CONFIG=read('publication_topics.json');TOPICS=TOPIC_CONFIG['topics']
PROFILE=read('academic_profile.json')
SEARCH_IDENTITY=read('search_identity.json')
paper_pdf_targets(ALL_PAPERS,read('assets.json'))
SUMMARIES=read('paper_summaries.json')['entries']
assert {r['id'] for r in PAPERS} <= set(SUMMARIES), 'Every indexed paper needs an evidence-based reading summary.'
for rec in ALL_PAPERS:
 if not rec.get('visible',True):
  # Remove generated pages only; retain all original/local manuscript files.
  for generated in ['index.qmd','_metadata-head.html']:
   (S/'papers'/rec['slug']/generated).unlink(missing_ok=True)
  (S/'_site/papers'/rec['slug']/'index.html').unlink(missing_ok=True)
H=escape
def text(raw):
 class Extract(HTMLParser):
  def __init__(self):super().__init__();self.parts=[]
  def handle_data(self,s):self.parts.append(s)
 e=Extract();e.feed(raw);return ''.join(e.parts)
def stamp(b,page,tag=None):
 raw=b['html']
 if tag:
  root=re.match(r'<(\w+)',raw).group(1);raw=re.sub(r'^<'+root,r'<'+tag,raw);raw=re.sub(r'</'+root+r'>$','</'+tag+'>',raw)
 return raw.replace('>',f' data-source-page="{page}" data-source-block="{b["source_block"]}">',1)
def blocks(items,page,headings=()):
 out='';in_list=False
 for b in items:
  if b['tag']=='li':
   if not in_list:out+='<ul>';in_list=True
  elif in_list:out+='</ul>';in_list=False
  raw=stamp(b,page,'h2' if b['source_block'] in headings else None)
  if b['source_block'] in headings:raw=raw.replace('>', ' class="section-heading">',1)
  out+=raw+'\n'
 if in_list:out+='</ul>'
 return out
def note(msg):return '<div class="review-note" role="note"><p>'+H(msg)+'</p></div>'
def academic_profile():
 # One reusable, static profile on every page; no client-side injection required.
 b=PAGES['home']['blocks']
 links=blocks(b[6:7],'home')
 icons=iter(PROFILE['profile_icons'])
 links=re.sub(r'(<a\b[^>]*>)',lambda m:m.group(1)+'<i class="bi bi-'+next(icons)+'" aria-hidden="true"></i>',links)
 roles='<ul class="profile-roles">'+''.join('<li>'+H(role)+'</li>' for role in PROFILE['roles'])+'</ul>'
 address=PROFILE['address']
 location='<address class="profile-address"><i class="bi bi-geo-alt-fill" aria-hidden="true"></i><a href="'+H(address['url'],quote=True)+'">'+H(address['text'])+'</a></address>'
 return '<div class="home-profile site-profile" role="complementary" aria-label="Academic profile"><figure class="home-portrait"><img src="/assets/profile/profile.png" alt="Wenjun Zhu" width="905" height="936"></figure>'+blocks(b[1:2],'home')+roles+'<div class="profile-links">'+links+'</div>'+location+'</div>'
def biography_paragraph(paragraph,links=None):
 # Plain prose stays editable and testable; apply approved links/emphasis separately.
 rendered=H(paragraph)
 titles=sorted(PROFILE.get('about_italic_titles',[]),key=len,reverse=True)
 if titles:
  rendered=re.sub('|'.join(re.escape(H(title)) for title in titles),lambda m:'<em>'+m.group(0)+'</em>',rendered)
 for link in (PROFILE.get('about_links',[]) if links is None else links):
  rendered=rendered.replace(H(link['text']),'<a href="'+H(link['url'],quote=True)+'">'+H(link['text'])+'</a>')
 return rendered
def raw_qmd(path,title,body,classes='',lang=None,header_extra='',description=None):
 p=S/path;p.parent.mkdir(parents=True,exist_ok=True)
 front={'title':title,'pagetitle':title,'body-classes':('shared-profile-page '+classes).strip(),'toc':False}
 body=academic_profile()+'<div class="site-page-content">'+body+'</div>'
 if lang:front['lang']=lang
 identity=SEARCH_IDENTITY.get('home' if path=='index.qmd' else 'zh' if path=='zh/index.qmd' else '')
 if identity:
  front['pagetitle']=identity['title']
  front['title-prefix']=''
  description=identity['description']
  header_extra+='<meta property="og:title" content="'+H(identity['title'],quote=True)+'">\n'
  header_extra+='<meta property="og:description" content="'+H(identity['description'],quote=True)+'">\n'
  header_extra+='<meta property="og:site_name" content="'+H(SEARCH_IDENTITY['site_name'],quote=True)+'">\n'
  if BASE:
   profile={'@context':'https://schema.org','@type':'ProfilePage','@id':page_url(path)+'#profile','url':page_url(path),'name':identity['title'],'inLanguage':lang or 'en','mainEntity':{'@id':BASE+'#person'}}
   header_extra+='<script type="application/ld+json">'+json.dumps(profile,ensure_ascii=False).replace('</','<\\/')+'</script>\n'
   if path=='index.qmd':
    website={'@context':'https://schema.org','@type':'WebSite','@id':BASE+'#website','url':BASE,'name':SEARCH_IDENTITY['site_name'],'publisher':{'@id':BASE+'#person'},'inLanguage':['en','zh-Hans']}
    header_extra+='<script type="application/ld+json">'+json.dumps(website,ensure_ascii=False).replace('</','<\\/')+'</script>\n'
 if description is None:
  defaults={'index.qmd':'Wenjun Zhu, Associate Professor at Nanyang Technological University. Research, publications, teaching and academic news.','cv/index.qmd':'Curriculum vitae of Wenjun Zhu: education, academic appointments and professional service.','publications/index.qmd':'Publications by Wenjun Zhu, with individual paper pages, abstracts and existing public source links.','working-papers/index.qmd':'Selected working papers by Wenjun Zhu and coauthors, with abstracts and public source links.','research/index.qmd':'Wenjun Zhu’s research interests and projects in insurance, finance and risk management.','teaching/index.qmd':'Courses taught by Wenjun Zhu in actuarial science, finance and risk management.','news/index.qmd':'Academic news and upcoming presentations from Wenjun Zhu.','miscellaneous/index.qmd':'Personal interests and miscellaneous writing from Wenjun Zhu.','zh/index.qmd':PERSON['chinese_profile'],'review/index.qmd':'Local review notes and unresolved migration decisions.'}
  description=defaults.get(path,title)
 header_extra='<meta name="description" content="'+H(description,quote=True)+'">\n'+header_extra
 header_extra+='<meta name="robots" content="'+('index, follow' if PRODUCTION else 'noindex, nofollow')+'">\n'
 if PRODUCTION and path in ['index.qmd','zh/index.qmd']:
  for code,target in [('en','index.qmd'),('zh-Hans','zh/index.qmd'),('x-default','index.qmd')]:header_extra+='<link rel="alternate" hreflang="'+code+'" href="'+H(page_url(target),quote=True)+'">\n'
 if header_extra:
  header=p.parent/'_metadata-head.html';header.write_text(header_extra)
  front['include-in-header']=[str(header.relative_to(S))]
  # Quarto resolves document includes relative to the document, not root.
  import os
  front['include-in-header']=[os.path.relpath(S/x,p.parent) for x in front['include-in-header']]
 lines=['---']+[f'{k}: {json.dumps(v,ensure_ascii=False)}' for k,v in front.items()]+['---','','```{=html}',body,'```','']
 p.write_text('\n'.join(lines))
def news_items(heading_level=3):
 assert heading_level in [2,3]
 out=''
 for e in sorted(NEWS['entries'],key=lambda x:x['date'],reverse=True):
  if not e.get('visible',True):continue
  category='<span class="news-category">'+H(e['category'])+'</span>' if e.get('category') else ''
  label='<span class="upcoming">'+H(e['label'])+'</span>' if e.get('label') else ''
  description=H(e['text'])
  if e.get('url') and e.get('inline_link_text'):
   label_text=H(e['inline_link_text'])
   assert e['inline_link_text'] in e['text'], 'Inline News link must match its visible description.'
   description=description.replace(label_text,'<a href="'+H(e['url'],quote=True)+'">'+label_text+'</a>',1)
   url=''
  else:
   url=' <a href="'+H(e['url'],quote=True)+'">'+H(e.get('link_label','Read more'))+'</a>' if e.get('url') else ''
  if e.get('backup_url'):
   url+=' · <a href="'+H(e['backup_url'],quote=True)+'">'+H(e['backup_label'])+'</a>'
  if e.get('announcement_url'):
   url+=' <a href="'+H(e['announcement_url'],quote=True)+'">'+H(e.get('announcement_link_label','Official announcement'))+'</a>'
  elif e.get('announcement_pending'):
   url+='<span class="news-pending">Official award announcement: pending.</span>'
  when=('<span class="news-year">'+H(e['display_date'])+'</span>') if e.get('date_precision')=='year' else ('<time datetime="'+H(e['date'],quote=True)+'">'+H(e['display_date'])+'</time>')
  title='<h'+str(heading_level)+' class="news-title">'+H(e['title'])+'</h'+str(heading_level)+'>'
  out+=f'<article class="news-entry" data-news-id="{H(e["id"])}"><div>{when}{category}{label}</div><div class="news-copy">{title}<p class="news-description">{description}{url}</p></div></article>'
 return out
def figures(rec,detail=False):
 if not rec['figures']:return ''
 out='<div class="paper-figures">';carousel=len(rec['figures'])>1
 if carousel:out+='<div data-carousel data-interval="6500" role="region" aria-roledescription="carousel" aria-label="Research figures">'
 for f in rec['figures']:
  src='/'+f['path'];out+='<figure'+(' class="carousel-slide"' if carousel else '')+'><a href="'+src+'"><img src="'+src+'" alt="'+H(f['alt'],quote=True)+'" loading="lazy"></a>'
  if f.get('caption'):out+='<figcaption>'+H(f['caption'])+'</figcaption>'
  out+='</figure>'
 if carousel:out+='<div class="carousel-controls" hidden><button type="button" data-previous aria-label="Previous research figure">Previous</button><span class="carousel-status" aria-live="off">Figure 1 of '+str(len(rec['figures']))+'</span><button type="button" data-toggle aria-label="Pause automatic figure switching">Pause</button><button type="button" data-next aria-label="Next research figure">Next</button></div></div>'
 return out+'</div>'
def paper_body(rec,detail=False):
 page='working-papers' if rec['collection']=='working' else 'publication'
 body=blocks(rec['body'],page)
 if rec['figures'] and not detail:return '<div class="paper-body has-figure"><div class="paper-text">'+body+'</div>'+figures(rec)+'</div>'
 return '<div class="paper-abstract">'+body+'</div>'+figures(rec,True)
def author_display(value):
 # Preserve the original author spelling/order and student markers.
 return re.sub(r'Wenjun Zhu|Zhu,? W\.|W\. Zhu',lambda m:'<strong>'+m[0]+'</strong>',H(value))
def resource_links(rec,exclude=()):
 links=[]
 for item in rec['display']['links']:
  if not item.get('url'):
   links.append('<span class="resource-pending">'+H(item['label'])+' <span>(pending)</span></span>')
   continue
  if item['url'] in exclude:continue
  label='Publisher' if item['label']=='DOI' and exclude else item['label']
  links.append('<a href="'+H(item['url'],quote=True)+'">'+H(label)+'</a>')
 return '<div class="paper-resources">'+'<span aria-hidden="true"> · </span>'.join(links)+'</div>' if links else ''
def entry(rec):
 d=rec['display'];topic_ids=rec['topics']
 m=rec['metadata']
 # Search bibliographic content only; verification dates/provenance are not publication dates.
 metadata_text=[str(m.get(key) or '') for key in ['title','journal_title','book_title','publication_date','publication_year','online_date','doi']]+m.get('authors',[])
 search=' '.join([rec['title'],d['authors'],d['publication'],d['notes'],SUMMARIES[rec['id']],*metadata_text,*[b['text'] for b in rec['body']]])
 venue=m.get('journal_title') or m.get('book_title') or d['publication']
 number='<span class="paper-number">['+str(rec['display_number'])+']</span> ' if rec['display_number'] is not None else ''
 out='<article class="paper-entry" id="'+rec['id']+'" data-paper-id="'+rec['id']+'" data-topics="'+' '.join(topic_ids)+'" data-search-venue="'+H(venue,quote=True)+'" data-search="'+H(search,quote=True)+'"><h3 class="paper-page-link">'+number+'<a href="/papers/'+rec['slug']+'/index.html">'+H(rec['title'])+'</a></h3>'
 out+='<div class="paper-entry-layout'+(' has-figure' if rec['figures'] else '')+'"><div class="paper-entry-copy">'
 out+='<p class="paper-authors">'+author_display(d['authors'])+'</p>'
 if d['publication']:out+='<p class="paper-venue">'+H(d['publication'])+'</p>'
 if d['notes']:out+='<p class="paper-history">'+H(d['notes'])+'</p>'
 out+='<p class="paper-summary">'+H(SUMMARIES[rec['id']])+'</p>'
 out+=resource_links(rec)
 out+='<ul class="paper-topics" aria-label="Research topics">'+''.join('<li>'+H(t['label'])+'</li>' for t in TOPICS if t['id'] in topic_ids)+'</ul>'
 out+='</div>'
 if rec['figures']:out+='<div class="paper-entry-visual">'+figures(rec)+'</div>'
 return out+'</div></article>'
def publication_controls(records,noun='publications'):
 out='<div class="publication-controls" hidden><div class="publication-search"><label for="publication-query">Search '+H(noun)+'</label><div class="publication-search-row"><input type="search" id="publication-query" placeholder="Title, author, journal, year or keyword" autocomplete="off" aria-controls="publication-results"><button type="button" data-clear>Reset</button></div></div><div class="topic-filters" role="group" aria-label="Filter '+H(noun)+' by research topic"><button type="button" data-topic="all" aria-pressed="true">All <span>('+str(len(records))+')</span></button>'
 for topic in TOPICS:
  count=sum(topic['id'] in r['topics'] for r in records)
  out+='<button type="button" data-topic="'+topic['id']+'" aria-pressed="false">'+H(topic['label'])+' <span>('+str(count)+')</span></button>'
 return out+'</div><p class="publication-count" role="status" aria-live="polite" aria-atomic="true"></p></div>'
# Approved profile revision; original English capture remains in data/pages.json.
b=PAGES['home']['blocks']
about=''.join('<p data-profile-paragraph="'+str(i)+'">'+biography_paragraph(p)+'</p>' for i,p in enumerate(PROFILE['about_paragraphs']))
home='<section class="home-intro"><div class="home-main">'+blocks(b[2:3],'home')+'<div class="home-copy">'+about+'</div></div></section>'
home+='<section class="news-section" aria-labelledby="news-heading"><div class="news-heading"><h2 id="news-heading">News</h2><a href="/news/index.html">All news</a></div><div class="news-scroll" tabindex="0" role="region" aria-label="News announcements; scroll for older items">'+news_items()+'</div></section>'
person_json=person_schema(PERSON)
raw_qmd('index.qmd','Home',home,'home-page',header_extra='<script type="application/ld+json">'+json.dumps(person_json,ensure_ascii=False).replace('</','<\\/')+'</script>')
# CV: selected local download only; the previous public link was removed by request.
b=PAGES['about']['blocks'];old_cv=re.search(r'href="([^"]+)"',b[1]['html']).group(1)
new_cv=b[1].copy();new_cv['html']=new_cv['html'].replace(old_cv,'/assets/cv/CV_WenjunZhu.pdf')
cv=stamp(new_cv,'about')+'<hr>'
cv+=blocks(b[2:19],'about',[2,11,14,18])
for institution,appointments in [(19,range(20,26)),(26,[27]),(28,[29])]:
 cv+='<section class="cv-institution">'+stamp(b[institution],'about','h3')+'<ul class="cv-appointments">'+''.join(stamp(b[i],'about','li') for i in appointments)+'</ul></section>'
cv+=blocks([b[30]],'about',[30])
for institution,appointment in [(31,32),(33,34)]:
 cv+='<section class="cv-institution">'+stamp(b[institution],'about','h3')+'<ul class="cv-appointments">'+stamp(b[appointment],'about','li')+'</ul></section>'
raw_qmd('cv/index.qmd','CV','<div class="cv-content">'+cv+'</div>')
# Publication and working-paper listings, using explicit original ordering.
conditional=[r for r in PAPERS if r['collection']=='conditional'];ref=[r for r in PAPERS if r['collection']=='refereed'];other=[r for r in PAPERS if r['collection']=='other'];wp=[r for r in PAPERS if r['collection']=='working']
assert [x['display_number'] for x in ref]==sorted({x['display_number'] for x in ref},reverse=True)
assert [x['display_number'] for x in other]==list(range(13,0,-1))
pub='<div data-publication-browser>'+publication_controls(conditional+ref+other)+'<div id="publication-results">'
if conditional:pub+='<section data-publication-group><h2 class="section-heading">Conditionally Accepted</h2>'+''.join(entry(r) for r in conditional)+'</section>'
pub+='<section data-publication-group>'+blocks([PAGES['publication']['blocks'][1]],'publication',[1])+''.join(entry(r) for r in ref)+'</section>'
pub+='<section data-publication-group>'+blocks([PAGES['publication']['blocks'][82]],'publication',[82])+''.join(entry(r) for r in other)+'</section></div><p class="publication-empty" hidden>No publications match this search. Try another term or reset the filters.</p>'
pub+='<div class="original-footnote">'+stamp(PAGES['publication']['blocks'][96],'publication')+'</div></div>'
raw_qmd('publications/index.qmd','PUBLICATION',pub)
wps='<div data-publication-browser data-item-label="working papers">'+publication_controls(wp,'working papers')+'<div id="publication-results" data-publication-group>'+''.join(entry(r) for r in wp)+'</div><p class="publication-empty" hidden>No working papers match this search. Try another term or reset the filters.</p><div class="original-footnote">'+stamp(PAGES['working-papers']['blocks'][18],'working-papers')+'</div></div>'
raw_qmd('working-papers/index.qmd','SELECTED WORKING PAPERS',wps)
b=PAGES['research']['blocks']
research=blocks(b[1:2],'research',[1])+'<p class="research-intro">'+H(PROFILE['research_intro'])+'</p><ul class="research-areas">'
research+=''.join('<li><strong>'+H(a['title'])+'.</strong> '+H(a['text'])+'</li>' for a in PROFILE['research_areas'])+'</ul>'
research+=blocks(b[7:8],'research',[7])+'<ul class="additional-grants">'+''.join('<li>'+H(g['display'])+'</li>' for g in PROFILE['additional_grants'])+'</ul>'
research+=blocks(b[8:21],'research')
raw_qmd('research/index.qmd','RESEARCH',research)
# Teaching columns become semantic rows. Only syllabus hrefs are removed by instruction.
b=PAGES['teaching']['blocks'];teach=note('Course materials will be added when the Teaching section is updated.')
for inst,starts,n in [(1,[2,11,20,29],8),(38,[39,42,45,48],2),(51,[52,54,56,58],1)]:
 teach+='<section class="teaching-institution">'+stamp(b[inst],'teaching')+'<div class="table-scroll" role="region" tabindex="0" aria-label="Course table"><table class="teaching-table"><thead><tr>'
 for s in starts:teach+='<th scope="col">'+stamp(b[s],'teaching','span')+'</th>'
 teach+='</tr></thead><tbody>'
 for row in range(n):
  teach+='<tr>'
  for c,s in enumerate(starts):
   item=b[s+1+row].copy()
   override=PROFILE.get('approved_source_text_overrides',{}).get('teaching',{}).get(str(item['source_block'])) if c==0 else None
   if override is not None:item['html']='<p>'+H(override)+'</p>'
   elif c==0:item['html']=re.sub(r'<a\b[^>]*>(.*?)</a>',r'<span>\1</span>',item['html'],flags=re.S)
   teach+='<td>'+stamp(item,'teaching','div')+'</td>'
  teach+='</tr>'
 teach+='</tbody></table></div></section>'
raw_qmd('teaching/index.qmd','TEACHING',teach)
raw_qmd('miscellaneous/index.qmd','MISCELLANEOUS',blocks(PAGES['miscellaneous']['blocks'][1:],'miscellaneous'))
raw_qmd('news/index.qmd','News','<section class="news-archive" aria-label="All news">'+news_items(2)+'</section>','news-page')
zh='<section class="zh-profile">'+''.join('<p>'+biography_paragraph(p,PERSON.get('chinese_links',[]))+'</p>' for p in PERSON['chinese_paragraphs'])+'</section><p><a href="/cv/index.html">英文简历</a> · <a href="/publications/index.html">发表论文</a> · <a href="/working-papers/index.html">工作论文</a> · <a href="/index.html">English</a></p>'
raw_qmd('zh/index.qmd','个人简介',zh,lang='zh-Hans',header_extra='<script type="application/ld+json">'+json.dumps(person_json,ensure_ascii=False).replace('</','<\\/')+'</script>',description='朱文君，南洋理工大学南洋商学院长聘副教授。研究气候变化、农业保险、死亡率与长寿风险，以及金融与保险中的统计和人工智能方法。')
# Each paper is a complete static document; lists are crawlable browse indexes.
for rec in PAPERS:
 base='working-papers' if rec['collection']=='working' else 'publications';page='working-papers' if rec['collection']=='working' else 'publication'
 m=rec['metadata'];paper_title=m.get('title',rec['title']) if m else rec['title']
 abstract_blocks=[b for b in rec['body'] if b['source_block'] in rec.get('abstract_source_blocks',[])]
 abstract='\n\n'.join(b['text'] for b in abstract_blocks)
 body='<p class="publication-kind">'+H(rec['publication_kind'])+'</p>'
 if m:
  detail_authors=rec['display'].get('detail_authors')
  body+='<p class="paper-authors">'+(author_display(detail_authors) if detail_authors else H('; '.join(m['authors'])))+'</p>'
  if m.get('doi'):
   publication=[m.get('journal_title') or m.get('book_title'),m.get('publication_date'),('Volume '+m['volume']) if m.get('volume') else None,('Issue '+m['issue']) if m.get('issue') else None,('Article '+m['article_number']) if m.get('article_number') else ('pp. '+m['page'] if m.get('page') else None)]
   body+='<p class="publication-details">'+H(' · '.join(v for v in publication if v))+'<br><a href="https://doi.org/'+H(m['doi'],quote=True)+'">DOI: '+H(m['doi'])+'</a>'
   if m.get('online_date'):body+='<br>Published online: '+H(m['online_date'])
   body+=' · <a href="citation.bib" download>Download citation (BibTeX)</a></p>'
   bib=S/'papers'/rec['slug']/'citation.bib';bib.parent.mkdir(parents=True,exist_ok=True);bib.write_text(bibtex(rec))
  elif rec.get('publication_status')=='conditionally_accepted' or rec['collection']=='conditional':body+='<p class="publication-details">Energy Economics · Conditionally accepted (October 2026)</p>'
  else:body+='<p class="publication-details">Working paper · '+H(m['publication_year'])+'</p>'
 else:
  body+='<p class="paper-authors">'+author_display(rec['display']['authors'])+'</p>'
  if rec['display']['publication']:body+='<p class="publication-details">'+H(rec['display']['publication'])+'</p>'
 body+=resource_links(rec,exclude=['https://doi.org/'+m['doi']] if m.get('doi') else [])
 if rec['display']['notes']:body+='<p class="paper-history">'+H(rec['display']['notes'])+'</p>'
 if abstract:
  body+='<section class="paper-abstract" aria-labelledby="abstract-heading"><h2 id="abstract-heading">Abstract</h2>'+blocks(abstract_blocks,page)+'</section>'
  keyword_blocks=[b for b in rec['body'] if b['text'].strip().startswith('Keywords:')]
  body+=blocks(keyword_blocks,page)
  extras=[b for b in rec['body'] if b not in abstract_blocks and b not in keyword_blocks]
  if extras:body+='<section class="paper-supporting"><h2>Related material</h2>'+blocks(extras,page)+'</section>'
  body+=figures(rec,True)
 else:body+='<p class="abstract-unavailable">No abstract was supplied on the original site for this item.</p>'
 body+='<p class="return-link"><a href="/'+base+'/index.html#'+rec['id']+'">Back to '+('Selected Working Papers' if rec['collection']=='working' else 'Publications')+'</a></p>'
 head=build_metadata(rec,abstract)
 description=(' '.join(abstract.split())[:240]+'…') if len(abstract)>240 else (abstract or rec['citation']['text'])
 raw_qmd('papers/'+rec['slug']+'/index.qmd',paper_title,body,'paper-page',header_extra=head,description=description)
# A local review centre makes unresolved decisions visible without altering academic copy.
review='<p>This local review page is excluded from the production website. Original citations remain archived below. Citation corrections and working-paper version decisions remain pending.</p><h2>Current launch settings</h2><p>GitHub account: zwjsoar. Selected initial address: https://zwjsoar.github.io/. No repository has been created and nothing has been uploaded or published.</p><h2>Ready to review</h2><ul><li><a href="/zh/index.html">中文 profile</a> — latest owner-supplied wording.</li><li><a href="/news/index.html">News</a> — including the Nanyang Awards 2026 booklet link.</li><li><a href="/cv/index.html">CV</a> — selected file, unchanged.</li><li><a href="/teaching/index.html">Teaching</a> — course list retained; syllabus labels removed.</li></ul><p>The supplied NBS logo and shared profile are implemented. Publications and Selected Working Papers use the same four overlapping research categories.</p>'
pdf_audit=S.parent/'planning/pdf-downloads-20261029/mapping.json'
if not PRODUCTION and pdf_audit.exists():
 audit=json.loads(pdf_audit.read_text());coverage=audit['coverage'];ready=sum(x['status']=='ready' for x in coverage)
 review+='<h2>PDF download coverage</h2><p>'+str(ready)+' of '+str(len(PAPERS))+' records have matched website PDFs. Originals remain unchanged. Earlier instructions keeping all local paper PDFs private have been superseded by the owner’s all-paper download policy. Existing external links remain.</p>'
 for status,heading in [('version_review','PDF versions needing clarification'),('missing_local_pdf','No matching local PDF found')]:
  review+='<h3>'+heading+'</h3><ul>'
  for item in coverage:
   if item['status']==status:
    rec=next(r for r in PAPERS if r['id']==item['paper_id'])
    review+='<li><a href="/papers/'+rec['slug']+'/index.html">'+H(rec['title'])+'</a>'+(': '+H(item['reason']) if status=='version_review' else '')+'</li>'
  review+='</ul>'
 review+='<h3>PDF size follow-up</h3><p>Three matched PDFs exceed Google Scholar’s stated 5 MB limit: [25] quantile neural networks, [18] weather index insurance and [8] remote sensing. Downloads remain available; no compression or source alteration was performed.</p>'
review+='<h2>Records requiring review</h2><ul class="issue-list">'
for r in PAPERS:
 if r['issues']:review+='<li><a href="/papers/'+r['slug']+'/index.html">'+H(r['title'])+'</a>: '+H(' '.join(r['issues']))+'</li>'
review+='</ul><p>The full citation-correction table remains in planning/citation_corrections.md in the project workspace. The initial GitHub Pages address is selected; repository creation, upload and publication remain deferred.</p>'
review+='<h2>Original citation archive</h2>'
for r in ALL_PAPERS:
 page='working-papers' if r['collection']=='working' else 'publication'
 review+='<details class="citation-archive"><summary>'+H(r['id']+' · '+r['title'])+'</summary>'+stamp(r['citation'],page)+'</details>'
if not PRODUCTION:raw_qmd('review/index.qmd','Review notes',review)
print('Prepared retained English pages, News, Chinese profile, review notes and '+str(len(PAPERS))+' individual paper records. Only explicitly owner-selected PDFs are included.')
