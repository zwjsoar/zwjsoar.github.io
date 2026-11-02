"""Render citation metadata from reviewed structured fields (no network calls)."""
from html import escape
import json,re
from build_context import BASE
def meta(name,value):
 return '<meta name="'+name+'" content="'+escape(str(value),quote=True)+'">\n' if value else ''
def build_metadata(rec,abstract):
 m=rec['metadata'];head='';authors=[]
 if m:
  authors=m['authors']
  fields=[('citation_title',m.get('title',rec['title'])),*[('citation_author',a) for a in authors],('citation_publication_date',m.get('publication_date',m.get('publication_year'))),('citation_doi',m.get('doi')),('citation_journal_title',m.get('journal_title')),('citation_book_title',m.get('book_title')),('citation_volume',m.get('volume')),('citation_issue',m.get('issue')),('citation_article_number',m.get('article_number'))]
  for issn in m.get('issn',[]):fields.append(('citation_issn',issn))
  for isbn in m.get('isbn',[]):fields.append(('citation_isbn',isbn))
  # An electronic article number is not fabricated into a page range.
  if m.get('page') and not m.get('article_number'):
   pages=re.split(r'[-–]',m['page'],maxsplit=1);fields.append(('citation_firstpage',pages[0]))
   if len(pages)==2:fields.append(('citation_lastpage',pages[1]))
  head=''.join(meta(k,v) for k,v in fields)
 sd={'@context':'https://schema.org','@type':rec.get('schema_type','CreativeWork'),'name':m.get('title',rec['title']) if m else rec['title'],'inLanguage':'en','genre':rec.get('publication_kind','Publication')}
 if BASE:sd.update({'@id':BASE+'papers/'+rec['slug']+'/#work','url':BASE+'papers/'+rec['slug']+'/'})
 entities=[]
 for i,name in enumerate(authors):
  person={'@type':'Person','name':name}
  if BASE and name in ['Wenjun Zhu','Zhu, W.']:person['@id']=BASE+'#person'
  a=m.get('author_entities',[])
  if i<len(a) and a[i].get('ORCID'):person['sameAs']=a[i]['ORCID']
  entities.append(person)
 if entities:sd['author']=entities
 if abstract:sd['abstract']=abstract
 if rec.get('keywords'):sd['keywords']=rec['keywords']
 if rec['collection']=='working':sd['genre']='Working paper'
 if m:
  if rec.get('publication_status')=='conditionally_accepted' or rec['collection']=='conditional':sd['creativeWorkStatus']='Conditionally accepted'
  elif m.get('publication_date',m.get('publication_year')):sd['datePublished']=m.get('publication_date',m.get('publication_year'))
  if m.get('doi'):
   sd['identifier']={'@type':'PropertyValue','propertyID':'DOI','value':m['doi']};sd['sameAs']='https://doi.org/'+m['doi']
  if m.get('publisher'):sd['publisher']={'@type':'Organization','name':m['publisher']}
  if m.get('journal_title'):
   part={'@type':'Periodical','name':m['journal_title']}
   if m.get('issn'):part['issn']=m['issn']
   if m.get('volume'):part={'@type':'PublicationVolume','volumeNumber':m['volume'],'isPartOf':part}
   if m.get('issue'):part={'@type':'PublicationIssue','issueNumber':m['issue'],'isPartOf':part}
   sd['isPartOf']=part
  if m.get('book_title'):sd['isPartOf']={'@type':'Book','name':m['book_title']}
  if m.get('article_number'):sd['pagination']=m['article_number']
  elif m.get('page'):
   pages=re.split(r'[-–]',m['page'],maxsplit=1);sd['pageStart']=pages[0]
   if len(pages)==2:sd['pageEnd']=pages[1]
 # Only mapped main PDFs receive PDF metadata; held/missing files have no invented URL.
 if rec.get('public_pdf') and BASE:
  pdf_url=BASE+rec['public_pdf'].lstrip('/')
  head+=meta('citation_pdf_url',pdf_url)
  sd['encoding']={'@type':'MediaObject','contentUrl':pdf_url,'encodingFormat':'application/pdf'}
 return head+'<script type="application/ld+json">'+json.dumps(sd,ensure_ascii=False).replace('</','<\\/')+'</script>'
def bibtex(rec):
 m=rec['metadata'];kind='incollection' if m['type']=='book-chapter' else 'article'
 authors=' and '.join(a.get('family','')+', '+a.get('given','') for a in m['author_entities'])
 fields={'title':m['title'],'author':authors,'year':m['publication_year'],'journal':m.get('journal_title'),'booktitle':m.get('book_title'),'publisher':m.get('publisher') if kind=='incollection' else None,'volume':m.get('volume'),'number':m.get('issue'),'pages':m.get('page') if not m.get('article_number') else None,'eid':m.get('article_number'),'doi':m['doi'],'url':'https://doi.org/'+m['doi']}
 def safe(s):return str(s).replace('\\','\\textbackslash{}').replace('{','\\{').replace('}','\\}').replace('&','\\&').replace('%','\\%').replace('#','\\#').replace('_','\\_')
 return '@'+kind+'{'+rec['id'].replace('-','')+',\n'+',\n'.join('  '+k+' = {'+(str(v) if k in ['doi','url'] else safe(v))+'}' for k,v in fields.items() if v)+'\n}\n'
