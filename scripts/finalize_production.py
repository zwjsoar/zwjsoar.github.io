"""Generate production URL identity/robots/sitemap after Quarto has rendered."""
from build_context import ROOT,BASE,PRODUCTION
from urllib.parse import urlsplit
from html import escape
import re,xml.etree.ElementTree as ET
if not PRODUCTION:raise SystemExit('Production post-render hook used outside production')
out=ROOT/'_site-production';prefix=urlsplit(BASE).path.rstrip('/')
urls=[]
for p in sorted(out.rglob('*.html')):
 rel=p.relative_to(out).as_posix()
 if rel.startswith(('review/','opportunities/')):raise SystemExit('Review-only page unexpectedly rendered')
 canonical=BASE+rel.removesuffix('index.html')
 s=p.read_text()
 s=re.sub(r'<link\b(?=[^>]*\brel=["\']canonical["\'])[^>]*>\s*','',s,flags=re.I)
 s=s.replace('</head>','<link rel="canonical" href="'+escape(canonical,quote=True)+'">\n</head>',1)
 if prefix:
  # Preserve root-oriented source links when hosted under a GitHub project path.
  def rooted(m):
   path=m[2]
   return m[1]+(path if path==prefix or path.startswith(prefix+'/') else prefix+path)+m[3]
  s=re.sub(r'((?:href|src)=["\'])(/(?!/)[^"\']*)(["\'])',rooted,s)
 p.write_text(s);urls.append(canonical)
ns='http://www.sitemaps.org/schemas/sitemap/0.9';ET.register_namespace('',ns);tree=ET.Element('{'+ns+'}urlset')
for url in urls:ET.SubElement(ET.SubElement(tree,'{'+ns+'}url'),'{'+ns+'}loc').text=url
ET.ElementTree(tree).write(out/'sitemap.xml',encoding='utf-8',xml_declaration=True)
(out/'robots.txt').write_text('User-agent: *\nAllow: /\n\nSitemap: '+BASE+'sitemap.xml\n')
(out/'.nojekyll').write_text('')
print('Production URL identity and sitemap generated for '+str(len(urls))+' HTML pages; no publication performed.')
