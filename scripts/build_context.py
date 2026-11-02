"""Shared build identity; ordinary renders always remain private review builds."""
from pathlib import Path
from urllib.parse import urlsplit
import os,json
ROOT=Path(__file__).resolve().parents[1]
PRODUCTION='production' in os.environ.get('QUARTO_PROFILE','').split(',')
BASE=os.environ.get('ACADEMIC_SITE_URL','').rstrip('/')+'/' if PRODUCTION else None
if PRODUCTION:
 if os.environ.get('ACADEMIC_STAGED_BUILD')!='1':raise SystemExit('Use scripts/build_production.py: production renders must run in an isolated staging folder.')
 parts=urlsplit(BASE or '')
 if parts.scheme!='https' or not parts.netloc or parts.query or parts.fragment or parts.username or parts.password:raise SystemExit('An explicit valid HTTPS site URL is required.')
def page_url(path):
 path=str(path).replace('index.qmd','').replace('index.html','').lstrip('/')
 return BASE+path if BASE else None
def person_schema(person):
 p={'@context':'https://schema.org','@type':'Person','name':person['name'],'alternateName':person['chinese_name'],'jobTitle':person.get('job_titles',['Associate Professor (with tenure)']),'worksFor':{'@type':'Organization','name':'Nanyang Technological University'},'affiliation':{'@type':'Organization','name':'Nanyang Business School'},'sameAs':person.get('same_as',[])}
 if person.get('awards'):p['award']=person['awards']
 if BASE:p.update({'@id':BASE+'#person','url':BASE,'image':BASE+'assets/profile/profile.png'})
 return p
