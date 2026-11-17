from pathlib import Path
from html.parser import HTMLParser
from html import escape,unescape
from urllib.parse import urlsplit,urlunsplit,unquote
import re,json,posixpath,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
BASE='https://toshapetrov.ru'
ZH=json.loads((ROOT/'translations/zh.json').read_text())
EN=json.loads((ROOT/'translations/en.json').read_text())
RUFILES=[p.relative_to(ROOT).as_posix() for p in sorted(ROOT.rglob('*.html')) if p.relative_to(ROOT).parts[0] not in ['en','zh','pet'] and not p.name.startswith(('google','yandex'))]
ZHFILES=['index.html','art-statement.html','portfolio.html','exhibitions.html','contact.html','links.html']+['exhibitions/'+s+'.html' for s in ['defile-v-kostyumah-lva-baksta-2026','obrazy-pamyati-2025','u-reki-dva-berega-2026','meoldica-gazgolder-2025','lenovo-2024','okno-v-pamyat-2026']]
normalize=lambda s:' '.join(s.split())
def tr(s):
 key=normalize(s)
 if re.search('[А-Яа-яЁё]',key):
  if key not in EN:raise ValueError('Missing English translation: '+key)
  return EN[key]
 return key

def url(lang,rel):
 prefix='' if lang=='ru' else lang+'/'
 return BASE+'/'+prefix+('' if rel=='index.html' else rel)

def dest(lang,rel):return rel if lang=='ru' else lang+'/'+rel

def person(lang):
 return {'@type':'Person','@id':BASE+'/#person','name':'Tosha Petrov' if lang!='ru' else 'Тоша Петров','alternateName':['Тоша Петров','Tosha Petrov','St Laurent Jr','StLaurentJr'],'url':BASE+'/','image':BASE+'/images/artist/tosha-petrov.webp','jobTitle':{'ru':'Медиахудожник','en':'Media artist','zh':'媒体艺术家'}[lang],'description':{'ru':'Медиахудожник из Санкт-Петербурга. Занимается генеративным искусством с 2021 года, работает с видео, анимацией и инсталляцией.','en':'Media artist based in Saint Petersburg, working with generative art since 2021. His practice includes video, animation and installation.','zh':'常驻圣彼得堡的媒体艺术家，自2021年起从事生成艺术，创作涵盖视频、动画与装置。'}[lang],'homeLocation':{'@type':'Place','name':{'ru':'Санкт-Петербург','en':'Saint Petersburg','zh':'圣彼得堡'}[lang]},'sameAs':['https://t.me/stlaurentjr','https://instagram.com/stlaurentjr','https://www.youtube.com/@stlaurentjr','https://www.tiktok.com/@toshapetrov_tut','https://twitter.com/stlaurentjr','https://civitai.com/user/stlaurentjr']}

def schema(lang,rel,title):
 page_type='ContactPage' if rel=='contact.html' else 'CollectionPage' if rel in ['portfolio.html','exhibitions.html','press.html'] else 'WebPage'
 page={'@type':page_type,'@id':url(lang,rel)+'#webpage','url':url(lang,rel),'name':title,'inLanguage':{'ru':'ru','en':'en','zh':'zh-Hans'}[lang],'about':{'@id':BASE+'/#person'},'isPartOf':{'@id':BASE+'/#website'}}
 if rel=='art-statement.html':page['@type']='ProfilePage';page['mainEntity']={'@id':BASE+'/#person'}
 return '<script type="application/ld+json">'+json.dumps({'@context':'https://schema.org','@graph':[person(lang),{'@type':'WebSite','@id':BASE+'/#website','url':BASE+'/','name':'Tosha Petrov','inLanguage':['ru','en','zh-Hans'],'publisher':{'@id':BASE+'/#person'}},page]},ensure_ascii=False,separators=(',',':'))+'</script>'

class Inspect(HTMLParser):
 def __init__(self):super().__init__();self.title='';self.intitle=False;self.intro=False;self.desc='';self.introparts=[]
 def handle_starttag(self,t,a):
  a=dict(a)
  if t=='title':self.intitle=True
  if t=='p' and a.get('class') in ['participation','intro']:self.intro=True
  if t=='meta' and a.get('name')=='description':self.desc=a.get('content','')
 def handle_endtag(self,t):
  if t=='title':self.intitle=False
  if t=='p':self.intro=False
 def handle_data(self,d):
  if self.intitle:self.title+=d
  if self.intro:self.introparts.append(d)

def original_heading(rel):
 match=re.search(r'<h1[^>]*>(.*?)</h1>',(ROOT/rel).read_text(),re.S)
 return normalize(unescape(re.sub('<[^>]+>','',match[1]))) if match else ''

ORIGINAL_NAMES=list(dict.fromkeys([original_heading(rel).strip('«»') for rel in RUFILES if rel.startswith('exhibitions/')]+['Избыточность','Катарсис','У реки два берега','Окно в память','Хи-хи ха-ха','Седьмой сон','Куда идёт «новое» искусство?']))
def with_original(source,translated):
 if not re.search('[А-Яа-яЁё]',source):return translated
 # Only title labels, never the surrounding descriptive paragraphs.
 matches=[name for name in ORIGINAL_NAMES if name in source and re.search('[А-Яа-яЁё]',name)]
 matches=[name for name in matches if not any(name!=other and name in other for other in matches)]
 return translated+(' · '+ ' / '.join('«'+name+'»' for name in matches) if matches else '')

class Translate(HTMLParser):
 def __init__(self,rel,lang='en'):
  super().__init__(convert_charrefs=False);self.rel=rel;self.lang=lang;self.tag='';self.dictionary=EN if lang=='en' else ZH;self.out=[];self.skip=0;self.page=Inspect();self.page.feed(clean_source((ROOT/rel).read_text()));self.title=with_original(self.page.title,self.translate(self.page.title)) if rel.startswith('exhibitions/') else self.translate(self.page.title)
 def translate(self,s):
  key=normalize(s)
  if re.search('[А-Яа-яЁё]',key):
   if key not in self.dictionary:raise ValueError('Missing '+self.lang+' translation: '+key)
   return self.dictionary[key]
  return key
 def attrs(self,tag,attrs):
  a=dict(attrs)
  if tag=='html':a['lang']='zh-Hans' if self.lang=='zh' else 'en'
  for key in ['href','src','poster']:
   if key not in a:continue
   u=urlsplit(a[key])
   if u.scheme or u.netloc or not u.path:continue
   target=posixpath.normpath(posixpath.join(posixpath.dirname(self.rel),unquote(u.path))) if not u.path.startswith('/') else u.path.lstrip('/')
   if target in RUFILES:target=(self.lang if self.lang=='en' or target in ZHFILES else 'en')+'/'+target
   a[key]=urlunsplit(('','',posixpath.relpath(target,posixpath.dirname(self.lang+'/'+self.rel)),u.query,u.fragment))
  for key in ['alt','aria-label','title']:
   if key in a and a[key] and re.search('[А-Яа-яЁё]',a[key]):
    k=normalize(a[key])
    a[key]=self.dictionary.get(k,{'alt':self.title+(' — image' if self.lang=='en' else ' — 图片'),'aria-label':('Open image' if tag=='a' else 'Video' if tag=='video' else 'Navigation') if self.lang=='en' else ('查看图片' if tag=='a' else '视频' if tag=='video' else '导航'),'title':self.title}[key])
  if tag=='meta':
   name=a.get('name') or a.get('property')
   if name in ['og:title','twitter:title']:a['content']=self.title
   if name in ['description','og:description','twitter:description']:
    intro=normalize(''.join(self.page.introparts));a['content']=self.translate(intro) if intro and intro in self.dictionary else self.title+('. Video art, animation, exhibitions and projects.' if self.lang=='en' else '。视频艺术、动画、展览与项目。')
   if name in ['og:image:alt','twitter:image:alt']:a['content']=self.title
   if name=='author':a['content']='Tosha Petrov'
   if name=='og:locale':a['content']='en_GB' if self.lang=='en' else 'zh_CN'
   if name=='og:site_name':a['content']='Tosha Petrov'
   if name=='og:url':a['content']=url(self.lang,self.rel)
  if tag=='link' and a.get('rel')=='canonical':a['href']=url(self.lang,self.rel)
  return ''.join(' '+k+(('="'+escape(v,quote=True)+'"') if v is not None else '') for k,v in a.items())
 def handle_starttag(self,t,a):
  self.tag=t
  self.out.append('<'+t+self.attrs(t,a)+'>')
  if t in ['script','style']:self.skip+=1
 def handle_startendtag(self,t,a):
  self.tag=t
  self.out.append('<'+t+self.attrs(t,a)+'>')
 def handle_endtag(self,t):
  self.tag=''
  self.out.append('</'+t+'>')
  if t in ['script','style']:self.skip-=1
 def handle_data(self,d):
  if self.skip or not d.strip():self.out.append(d);return
  leading=re.match(r'^\s*',d).group(0);trailing=re.search(r'\s*$',d).group(0)
  translated=self.translate(d)
  if self.tag in ['h1','h2','h3','a','title']:translated=with_original(normalize(d),translated)
  self.out.append(leading+escape(translated,quote=False)+trailing)
 def handle_entityref(self,n):self.out.append('&'+n+';')
 def handle_charref(self,n):self.out.append('&#'+n+';')
 def handle_decl(self,d):self.out.append('<!'+d+'>')
 def handle_comment(self,d):pass

def language_nav(lang,rel):
 labels={'ru':'ру','en':'en','zh':'中文'};items=[];parent=posixpath.dirname(dest(lang,rel))
 for target in ['ru','en','zh']:
  available=target!='zh' or rel in ZHFILES
  target_rel=rel if available else 'index.html'
  label=labels[target]
  href=posixpath.relpath(dest(target,target_rel),parent or '.')
  current=' aria-current="page"' if target==lang else ''
  hint=' title="'+{'ru':'Китайская версия: главная страница','en':'Chinese version: home page','zh':'中文首页'}[lang]+'"' if not available else ''
  items.append('<a href="'+href+'"'+hint+' lang="'+('zh-Hans' if target=='zh' else target)+'" hreflang="'+('zh-Hans' if target=='zh' else target)+'"'+current+'>'+label+'</a>')
 return '<nav class="language-nav" aria-label="'+{'ru':'Язык сайта','en':'Language','zh':'语言'}[lang]+'">'+'<span aria-hidden="true">/</span>'.join(items)+'</nav>'

def navigation_source(text):
 text=re.sub(r'<details class="mobile-menu">.*?</details>\s*','',text,flags=re.S)
 return text.replace('class="site-nav site-nav-desktop"','class="site-nav"')

def responsive_navigation(text,lang):
 text=navigation_source(text)
 def render(match):
  nav=match[0]
  label={'ru':'Меню','en':'Menu','zh':'菜单'}[lang]
  return nav.replace('class="site-nav"','class="site-nav site-nav-desktop"',1)+'\n<details class="mobile-menu"><summary>'+label+'<span class="menu-symbol" aria-hidden="true"></span></summary>'+nav+'</details>'
 return re.sub(r'<nav class="site-nav"[^>]*>.*?</nav>',render,text,flags=re.S)

METRICA_SCRIPT='<script type="text/javascript" >\n   (function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};\n   m[i].l=1*new Date();\n   for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}\n   k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})\n   (window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");\n\n   ym(102196430, "init", {\n        clickmap:true,\n        trackLinks:true,\n        accurateTrackBounce:true,\n        webvisor:true\n   });\n</script>'
METRICA_NOSCRIPT='<noscript><div><img src="https://mc.yandex.ru/watch/102196430" style="position:absolute;left:-9999px;" alt=""></div></noscript>'

def ensure_metrica(text):
 # Keep the existing counter and settings, and initialize it exactly once.
 text=re.sub(r'<script\b[^>]*>.*?</script>\s*',lambda m:'' if re.search(r'ym\(\s*102196430\s*,',m[0]) else m[0],text,flags=re.S)
 text=re.sub(r'<noscript\b[^>]*>.*?</noscript>\s*',lambda m:'' if 'mc.yandex.ru/watch/102196430' in m[0] else m[0],text,flags=re.S)
 charset=re.search(r'<meta\s+charset=[^>]*>',text,re.I)
 position=charset.end() if charset else re.search(r'<head[^>]*>',text,re.I).end()
 text=text[:position]+'\n'+METRICA_SCRIPT+'\n'+text[position:].lstrip('\r\n')
 body=re.search(r'<body[^>]*>',text,re.I)
 if body:text=text[:body.end()]+'\n'+METRICA_NOSCRIPT+'\n'+text[body.end():].lstrip('\r\n')
 return text

def finalize(text,lang,rel):
 text=ensure_metrica(text)
 text=responsive_navigation(text,lang)
 # Rebuild generated metadata from current text; never add it to verification files.
 text=re.sub(r'<link\b[^>]*rel="alternate"[^>]*>\s*','',text)
 text=re.sub(r'<nav class="language-nav".*?</nav>\s*','',text,flags=re.S)
 text=re.sub(r'<script type="application/ld\+json">.*?</script>\s*','',text,flags=re.S)
 for target in ['ru','en','zh']:
  if target=='zh' and rel not in ZHFILES:continue
  text=text.replace('</head>','<link rel="alternate" hreflang="'+('zh-Hans' if target=='zh' else target)+'" href="'+url(target,rel)+'">\n</head>',1)
 text=text.replace('</head>','<link rel="alternate" hreflang="x-default" href="'+url('ru',rel)+'">\n</head>',1)
 i=Inspect();i.feed(text)
 text=text.replace('</head>',schema(lang,rel,i.title)+'\n</head>',1)
 text=re.sub(r'<div class="footer-row">(.*?)</div>',r'\1',text,flags=re.S)
 row=language_nav(lang,rel) if rel=='links.html' else '<div class="footer-row"><p class="footer-name">Тоша Петров / Tosha Petrov</p>'+language_nav(lang,rel)+'</div>'
 def footer(match):
  content=re.sub(r'<p(?: class="footer-name")?>\s*(?:Тоша Петров / Tosha Petrov|Tosha Petrov)\s*</p>','',match[2])
  return match[1]+content.strip()+row+'</footer>'
 if '</footer>' in text:
  text=re.sub(r'(<footer\b[^>]*>)(.*?)</footer>',footer,text,flags=re.S)
 else:
  text=text.replace('</body>','<footer class="site-footer">'+row+'</footer>\n</body>',1)
 return text

def clean_source(text):
 text=navigation_source(text)
 text=re.sub(r'<nav class="language-nav".*?</nav>\s*','',text,flags=re.S)
 text=re.sub(r'<div class="footer-row">(.*?)</div>',r'\1',text,flags=re.S)
 return re.sub(r'<script type="application/ld\+json">.*?</script>\s*','',text,flags=re.S)

def translated(rel,lang):
 parser=Translate(rel,lang);parser.feed(clean_source((ROOT/rel).read_text()))
 text=''.join(parser.out)
 if lang=='zh':text=text.replace('>媒体报道</a>','>媒体报道（英文）</a>')
 return text

def selected_chinese(rel):
 text=translated('index.html','zh')
 projects=[
 ('2026','okno-v-pamyat-2026','记忆之窗','ZIL文化中心，莫斯科','视频作品《在信息流中》，探讨信息过载与反复回归的信息消费习惯。'),
 ('2026','defile-v-kostyumah-lva-baksta-2026','列昂·巴克斯特服装影像秀','特列季亚科夫画廊，莫斯科','根据巴克斯特服装设计稿制作动画。'),
 ('2026','u-reki-dva-berega-2026','一河两岸','MIRA中心 · Collider，苏兹达尔','作品《显而易见／不易察觉》；与策展人紧密合作，负责所有参展作品的视频剪辑。'),
 ('2025','obrazy-pamyati-2025','记忆的影像','MOÑ剧院，喀山','为舞台项目创作视频艺术，探索身体、运动与记忆之间的关系。'),
 ('2025','meoldica-gazgolder-2025','净化 · Catharsis','MELODICA，Gazgolder，莫斯科','视频作品《净化》，展览主题为《过量》。'),
 ('2024','lenovo-2024','Lenovo · It’s Gonna Be a Good Good Summer','Lenovo','为舞蹈影像制作生成式视觉效果。')]
 title=('精选作品' if rel=='portfolio.html' else '精选展览与项目')+' — Tosha Petrov'
 intro='视频、动画与装置领域的部分项目。' if rel=='portfolio.html' else '按年份排列的部分展览与合作项目。'
 body='<main id="main-content"><header><h1>'+title.split(' — ')[0]+'</h1><p class="intro">'+intro+'</p></header>'
 for year,slug,name,venue,description in projects:
  original=original_heading('exhibitions/'+slug+'.html')
  if re.search('[А-Яа-яЁё]',original):name+=' · '+original
  if rel=='portfolio.html':
   previews={'okno-v-pamyat-2026':('okno-v-pamyat-2026/artwork-still.webp',1600,900),'u-reki-dva-berega-2026':('u-reki-dva-berega-2026/photo-04.webp',1672,941)}
   if slug in previews:body+='<figure><a href="exhibitions/'+slug+'.html"><img src="../images/'+previews[slug][0]+'" width="'+str(previews[slug][1])+'" height="'+str(previews[slug][2])+'" loading="lazy" decoding="async" alt="'+name+'"></a></figure>'
  body+='<section><h2><a href="exhibitions/'+slug+'.html">'+name+'</a></h2><p class="meta">'+year+' · '+venue+'</p><p>'+description+'</p></section>'
 if rel=='portfolio.html':
  body+='<section><h2><a href="https://t.me/addstickers/this_is_the_end" target="_blank" rel="noopener noreferrer">一切都结束了 · «Это конец»</a></h2><p>为Telegram创作的原创贴纸包。</p><p class="project-meta">累计使用超过2.54亿次，安装超过470万次。Telegram累计统计数据，截至<time datetime="2026-11-15">2026年11月15日</time>。</p></section>'
 body+='<p><a href="../en/'+rel+'">查看完整列表（英文） →</a></p></main>'
 text=re.sub(r'<main\b[^>]*>.*?</main>',lambda _:body,text,flags=re.S)
 text=re.sub(r'<title>.*?</title>','<title>'+title+'</title>',text,flags=re.S)
 text=re.sub(r'(<meta (?:property|name)="(?:og:title|twitter:title)" content=")[^"]*',lambda m:m[1]+title,text)
 text=re.sub(r'(<meta (?:property|name)="(?:description|og:description|twitter:description)" content=")[^"]*',lambda m:m[1]+intro,text)
 text=re.sub(r'(<link rel="canonical" href=")[^"]*',lambda m:m[1]+url('zh',rel),text)
 text=re.sub(r'(<meta property="og:url" content=")[^"]*',lambda m:m[1]+url('zh',rel),text)
 text=text.replace('href="index.html" aria-current="page"','href="index.html"')
 text=text.replace('href="'+rel+'">','href="'+rel+'" aria-current="page">',1)
 return text

def build():
 for rel in RUFILES:
  out=ROOT/'en'/rel;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(finalize(translated(rel,'en'),'en',rel))
 for rel in ZHFILES:
  text=selected_chinese(rel) if rel in ['portfolio.html','exhibitions.html'] else translated(rel,'zh')
  out=ROOT/'zh'/rel;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(finalize(text,'zh',rel))
 for rel in RUFILES:
  p=ROOT/rel;p.write_text(finalize(p.read_text(),'ru',rel))
 for p in (ROOT/'pet').rglob('*.html'):
  p.write_text(ensure_metrica(p.read_text()))
 ns='http://www.sitemaps.org/schemas/sitemap/0.9';ET.register_namespace('',ns)
 tree=ET.parse(ROOT/'sitemap.xml');root=tree.getroot();existing={e.text for e in root.iter('{'+ns+'}loc')}
 for lang,files in [('en',RUFILES),('zh',ZHFILES)]:
  for rel in files:
   address=url(lang,rel)
   if address not in existing:ET.SubElement(ET.SubElement(root,'{'+ns+'}url'),'{'+ns+'}loc').text=address
 tree.write(ROOT/'sitemap.xml',encoding='utf-8',xml_declaration=True)
 print('Built',len(RUFILES),'English and',len(ZHFILES),'Chinese pages; updated Russian structured data and sitemap.')

if __name__=='__main__':build()
