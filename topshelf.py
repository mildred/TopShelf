#! /usr/bin/env python
# -*- coding: utf-8 -*-
## epub.py
## See copyright notice at end of file

import zipfile
import uuid
import time
#try:
#  import tidy
#except:
#  pass

class Epub:

  all_files = {}
  # dictionnary indexed by filename containing a dictionnary with keys:
  #   'data': the content of the file
  #   'type': the mime type
  #   'id':   an unique identifier

  navigation = []
  # an array of dictionnaries containing the table of contents
  #   'file': the filename
  #   'title': the title of the entry
  #   'sub':   sub tables

  file_id = 1
  nxc_uid = ""
  nxc_title = "Table Of Contents"

  def __init__(self):
    self.ncx_uid   = uuid.uuid1();
    self.ncx_title = "Table Of Contents"
    self.file_id   = 1
    self.all_files  = {}
    self.navigation = []

  def tidy(self, code):
    try:
      options = dict(output_xhtml=1,
		    add_xml_decl=1,
		    add_xml_space=1,
		    indent=1,
		    anchor_as_name=0,
		    clean=1,
		    doctype="strict",
		    drop_proprietary_attributes=1,
		    enclose_block_text=1,
		    enclose_text=1,
		    logical_emphasis=1,
		    merge_divs=1,
		    merge_spans=1)
      return str(tidy.parseString(code, **options))
    except:
      return code

  def addfile(self, filename, content, type):
    self.all_files[filename] = {
      'data': content,
      'type': type,
      'id':   "file%i" % self.file_id
    }
    self.file_id += 1

  def make_zipinfo(self, filename, compress_type = zipfile.ZIP_DEFLATED):
    info = zipfile.ZipInfo(filename)
    info.compress_type = compress_type
    info.date_time = time.localtime(time.time())[:6]
    info.external_attr = 0644 << 16L
    return info

  def writeout(self, epub_name):

    epub = zipfile.ZipFile(epub_name, 'w')

    mimetype = self.make_zipinfo('mimetype')
    mimetype.compress_type = zipfile.ZIP_STORED
    epub.writestr(mimetype, 'application/epub+zip')

    epub.writestr("META-INF/container.xml","""<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="metadata.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>\n""")

    epub.writestr("metadata.opf", self.get_opf().encode('utf-8'))
    epub.writestr("toc.ncx",      self.get_toc().encode('utf-8'))

    for filename in self.all_files:
      info = self.make_zipinfo(filename)
      epub.writestr(info, self.all_files[filename]['data'])

    epub.close()


  def get_metainfo(self, info):
    if   info == "title":	res = ""
    elif info == "lang":	res = ""
    elif info == "ident":	res = ""
    elif info == "subject":	res = ""
    elif info == "description":	res = ""
    elif info == "relation":	res = ""
    elif info == "creator":	res = ""
    elif info == "publisher":	res = ""
    elif info == "date":	res = ""
    elif info == "rights":	res = ""
    if type(res) == str:
      res = res.decode('utf-8', 'replace')
    return res

  def get_opf(self):
    metadata = u"""  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"
      xmlns:dcterms="http://purl.org/dc/terms/"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:title>%s</dc:title>
    <dc:language xsi:type="dcterms:RFC3066">%s</dc:language>
    <dc:identifier id="dcidid" opf:scheme="URI">%s</dc:identifier>
    <dc:subject>%s</dc:subject>
    <dc:description>%s</dc:description>
    <dc:relation>%s</dc:relation>
    <dc:creator>%s</dc:creator>
    <dc:publisher>%s</dc:publisher>
    <dc:date xsi:type="dcterms:W3CDTF">%s</dc:date>
    <dc:rights>%s</dc:rights>
  </metadata>""" % (
      self.get_metainfo("title"),
      self.get_metainfo("lang"),
      self.get_metainfo("ident"),
      self.get_metainfo("subject"),
      self.get_metainfo("description"),
      self.get_metainfo("relation"),
      self.get_metainfo("creator"),
      self.get_metainfo("publisher"),
      self.get_metainfo("date"),
      self.get_metainfo("rights"))

    manifest  = '  <manifest>\n'
    manifest += '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n'
    for filename in self.all_files:
      f = self.all_files[filename]
      manifest += '    <item id="item_%s" href="%s" media-type="%s"/>\n' % (
	f['id'], filename, f['type'])
    manifest += '  </manifest>\n'

    spine  = '  <spine toc="ncx">\n'
    spine += self.navigate_opf(self.navigation)
    spine += '  </spine>\n'

    return u"""<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="dcidid"
   version="2.0">

%s

%s

%s

</package>""" % (metadata, manifest, spine)

  def navigate_opf(self, navigation, res = ""):
    for nav in navigation:
      type, a, b = self.all_files[nav['file']]['type'].partition('/')
      if type == "text" or type == "application":
	res += '    <itemref idref="item_%s"/>\n' % self.all_files[nav['file']]['id']
	res = self.navigate_opf(nav['sub'], res)
    return res


  def get_toc(self):
    map = ""
    depth = 0
    order = 1
    for nav in self.navigation:
      map, d, order = self.navigate_toc(nav, "    ", map, 0, order)
      if d > depth:
	depth = d
    toc = u"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="en">
  <head>
    <meta name="dtb:uid" content="%s"/>
    <meta name="dtb:depth" content="%d"/>
    <!--meta name="dtb:generator" content=""/-->
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>%s</text></docTitle>
  <navMap>
%s
  </navMap>
</ncx>""" % (self.ncx_uid, depth, self.ncx_title, map);
    return toc

  def navigate_toc(self, nav, indent = "", res = "", depth = 0, order = 1):
    depth += 1
    final_depth = depth
    indent2 = indent + "  "
    res += indent + '<navPoint id="navPoint_%d" playOrder="%d">\n' % (order, order)
    res += indent + '  <navLabel><text>%s</text></navLabel>\n' % nav["title"]
    res += indent + '  <content src="%s"/>\n' % nav["file"]
    order += 1
    for n in nav["sub"]:
      res, d, order = self.navigate_toc(n, indent2, res, depth, order)
      if d > final_depth:
	final_depth = d
    res += indent + "</navPoint>\n"
    return res, final_depth, order


#######################################################################
## Copyright (c) 2009 Mildred Ki'Lya <mildred593(at)online.fr>
##
## Permission is hereby granted, free of charge, to any person
## obtaining a copy of this software and associated documentation
## files (the "Software"), to deal in the Software without
## restriction, including without limitation the rights to use,
## copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the
## Software is furnished to do so, subject to the following
## conditions:
##
## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
## OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
## HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
## WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
## FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
## OTHER DEALINGS IN THE SOFTWARE.
#######################################################################
## kate: hl Python; indent-width 2; space-indent on; replace-tabs off;
## kate: tab-width 8; remove-trailing-space on;


#! /usr/bin/env python
# -*- coding: utf-8 -*-
## topshelf.py
## See copyright notice at end of file

if 'Epub' not in dir():
  from epub import Epub
from urllib2 import urlopen, HTTPError
from urlparse import urljoin
import os
import sys
import datetime
import re
try:
  import BeautifulSoup
  soup_ok=True
except:
  soup_ok=False



def make_filename(str):
  res = ""
  for c in str:
    if c.isalnum():
      res = res + c
    elif res[-1]!='_' and res!="":
      res = res + "_"
  return res


class TopShelf(Epub):

  downloaded_files = {}
  # dictionnary indexed by filename containing a dictionnary:
  #   'url':   The URL
  #   'parse': If the data was parsed

  download_cache = {}
  # dictionnary indexed by url, the value is a dictionnary:
  #   'Content-Type': The Content-Type
  #   'data'        : The data

  def __init__(self, url = None, layout="TopShelf", accept_regexp=None, delete_regexp=None, skip=False):
    Epub.__init__(self)
    self.downloaded_files = {}
    self.current_nav = self.navigation
    self.info_title  = ""
    self.info_url    = ""
    self.info_author = ""
    self.info_tags   = []
    self.info_date   = datetime.datetime.utcnow()
    self.raw         = layout == None
    self.layout      = layout
    self.replace     = []
    self.replace_show= False
    self.error       = False
    if accept_regexp:
      self.accept_regexp = re.compile(accept_regexp)
    else:
      self.accept_regexp = None
    if delete_regexp:
      self.delete_regexp = re.compile(delete_regexp)
    else:
      self.delete_regexp = None
    self.recursion_limit = None
    self.recursion_index = 0
    if url:
      self.parse_url(url, output=(not skip))

  def translate_url_to_name(self, url, modify=True, suffix=None):
    for df in self.downloaded_files:
      if self.downloaded_files[df]['url']    == url and \
         self.downloaded_files[df]['modify'] == modify:
	return df
    filename = os.path.basename(url.rstrip('/'))
    if not modify:
      filename = "content/resources/%s" % filename
    else:
      if filename == "resources": filename = "resources-1"
      filename = "content/%s" % filename
    base, dot, ext = filename.partition('.')
    if suffix and not len(ext):
      dot = '.'
      ext = suffix
      filename = base + dot + ext
    i = 2
    while filename in self.downloaded_files:
      filename = base + "-" + str(i) + dot + ext
      i = i + 1
    self.downloaded_files[filename] = {'url':url, 'modify':modify}
    return filename.decode('utf-8')

  def allow_url(self, url):
    if self.delete_regexp and self.delete_regexp.search(url):
      return False
    elif self.accept_regexp:
      return self.accept_regexp.search(url)
    else:
      return True

  def get_url(self, url, relative=False):
    url = self.parse_url(url, parse=False, toc=False)
    if relative and url:
      if url.startswith(relative):
	a, b, url = url.partition(relative)
      else:
	for i in range(url.count("/")):
	  url = "../" + url
    return url

  def open_url(self, url):
    if url in self.download_cache:
      return self.download_cache[url]
    f = None
    try:
      f = urlopen(url);
    except:
      url = url.replace('bigcloset.us', 'bigclosetr.us');
      try:
	f = urlopen(url);
      except:
	print("Error downloading: %s" % url);
	self.error = True
    if f:
      dta = {
	'Content-Type': f.info().getheader("Content-Type").replace('; charset=', ';charset='),
	'data'        : f.read()}
      f.close()
      self.download_cache[url] = dta
      return dta
    return None

  def parse_url(self, url, parse=True, output=True, toc=True):
    allow = self.allow_url(url)
    if output and not allow:
      print "Don't download:   %s" % (url)
      return None
    if not self.info_url and output and allow:
      self.info_url = url
    dta = self.open_url(url)
    if not dta:
      print "Fail to download: %s" % (url)
      return None
    else:
      filename = self.translate_url_to_name(url, parse)
      is_html  = ("text/html"         in dta['Content-Type']) or \
		 ("application/xhtml" in dta['Content-Type'])
      has_file = filename in self.all_files
      data = dta['data']
      if dta['Content-Type'] == "text/plain":
	is_html = True
	dta['Content-Type'] = "text/html"
	data = data.decode('utf-8').encode('ascii', 'xmlcharrefreplace')
	for i in range(0, 9) + range(11, 13) + range(14, 32):
	  data = data.replace(chr(i),  "&#%x;" % i)
	data = data.replace('&', '&amp;')
	data = data.replace('<', '&lt;')
	data = data.replace('>', '&gt;')
	#data = data.replace('\n\n', '</p>\n<p>')
	#data = data.replace('\n  ', '</p>\n<p>')
	data = re.sub('\r?\n(\r?\n|  )', '</p>\n<p>', data)
	data = re.sub('_([^_<>]+)_', '<em>\\1</em>', data)
	data = re.sub('\*([^\*<>]+)\*', '<strong>\\1</strong>', data)
	data = """<html><body>\n<h1>%s</h1>\n<p>%s</p>\n</body></html>""" % (
	  os.path.basename(url), data)
      if has_file:
	if parse and is_html:
	  if output:
	    print "Process file  %s" % filename
	  else:
	    print "Process file* %s" % filename
	else:
	  print "Use file      %s" % filename
      else:
	if parse and is_html:
	  if output:
	    print "Process file  %s:\t%s" % (filename, url)
	  else:
	    print "Process file* %s:\t%s" % (filename, url)
	else:
	  print "Download file %s:\t%s" % (filename, url)

      if parse and is_html:
	data = self.prefilter(data, filename, url)
	soup = BeautifulSoup.BeautifulSoup(data)
	content = self.parse_soup(soup, filename, url, output)
	if not has_file and output:
	  self.addfile(filename, content,     "application/xhtml+xml")
      else:
	if output and toc:
	  self.current_nav.append({
	    'file' : filename,
	    'title': filename.encode('utf-8'),
	    'sub'  : []})
	if not has_file and output:
	  self.addfile(filename, data, dta['Content-Type'])
      return filename

  def init_replace(self, r1, r2, show=False):
    #print "%s -> %s" % (r1,r2)
    self.replace.append( (r1,r2) )
    if show: self.replace_show = True

  def prefilter(self, code, filename, baseurl):
    if len(self.replace):
      for r1, r2 in self.replace:
	code = re.sub(r1, r2, code)
      if self.replace_show:
	print "== code =="
	print code
	print "== /code =="
    return code

  def parse_soup_topshelf(self, soup, filename, baseurl, output):
    page_title = soup.find("title")
    if page_title:
      page_title = page_title.renderContents().replace(" | TopShelf", "")
      page_title = page_title.replace(" | BigCloset TopShelf", "")
    else:
      page_title = os.path.basename(filename)
    submitted  = soup.find('span', attrs={'class':'submitted'})
    if output:
      if not self.info_title:
	self.info_title = page_title
      navigation_item = {
	'file' : filename,
	'title': page_title.decode('utf-8'),
	'sub'  : []}
      self.current_nav.append(navigation_item)
      self.current_nav = navigation_item['sub']

      tags = soup.find('span', attrs={'class':'taxonomy'})
      if tags:
	for a in tags.findAll('a', rel='tag'):
	  s = a.renderContents()
	  if s not in self.info_tags:
	    self.info_tags.append(s)

      if not self.info_author:
	try:
	  # Try first tag as author
	  self.info_author = self.info_tags[0]
	  if self.info_author == "New Author":
	    self.info_author = None
	except:
	  pass
	if not self.info_author and submitted:
	  # Use the submitter name
	  a = submitted.find('a', title="View user profile.")
	  if not a: a = submitted.find('a')
	  if a:
	    self.info_author = a.renderContents()
	  else:
	    a, b, info = submitted.renderContents().partition("ubmitted by ")
	    if not info:
	      a, b, info = submitted.renderContents().partition("wned by ")
	    info, a, b = info.partition(" on")
	    if len(info): self.info_author = info

    if submitted:
      submitted = submitted.renderContents()

    self.soup_remove_before(soup, soup.find('span', attrs={'class':'print-link'}))
    self.soup_remove_after (soup, soup.find('div',  attrs={'class':'book-navigation'}))

    nav  = soup.find('div', attrs={'class':'book-navigation'})
    if nav:
      list = nav.find('ul')
      if list:
	#for line in list.findAll("li"):
	for line in nav.findAll('li', attrs={'class':'leaf'}):
	  link  = line.find("a")
	  title = link.renderContents()
	  url   = link["href"]
	  url = urljoin(baseurl, url)
	  self.parse_url(url)
	for line in nav.findAll('li', attrs={'class':'collapsed'}):
	  link  = line.find("a")
	  title = link.renderContents()
	  url   = link["href"]
	  url = urljoin(baseurl, url)
	  self.parse_url(url)
      nav.extract()
    else:
      nav = soup.find('div',  attrs={'class': 'content'})
      if nav:
	self.soup_remove_after (soup, nav)
	div = nav.find('div', attrs={'class': 'vote-wrap'})
	if div:
	  font = div.findPreviousSibling('font')
	  if font:
	    self.soup_remove_after (soup, font)
	    font.extract()
	  else:
	    self.soup_remove_after (soup, div.previousSibling)
	    div.previousSibling.extract()

    body = soup.find('body')

    if submitted:
      txt = BeautifulSoup.NavigableString(submitted)
      p = BeautifulSoup.Tag(soup, 'p')
      em = BeautifulSoup.Tag(soup, 'em')
      em.insert(0, txt)
      p.insert(0, em)
      body.insert(0, p)

    p = BeautifulSoup.Tag(soup, 'p')
    a = BeautifulSoup.Tag(soup, 'a')
    a.insert(0, BeautifulSoup.NavigableString(baseurl))
    a['href'] = baseurl;
    p.insert(0, BeautifulSoup.NavigableString("Downloaded from: "))
    p.insert(1, a)
    p['style'] = 'font-size: 0.5em'
    body.append(p)

    soup = self.follow_links(soup, baseurl, recursive=False)
    soup = self.sanitize_soup(soup, baseurl)
    return soup.prettify()

  def parse_soup_raw(self, soup, filename, baseurl, output):
    page_title = soup.find("title")
    if page_title:
      page_title = page_title.renderContents()
    else:
      page_title = os.path.basename(filename)
    if output:
      if not self.info_title:
	self.info_title = page_title
      navigation_item = {
	'file' : filename,
	'title': page_title.decode('utf-8'),
	'sub'  : []}
      self.current_nav.append(navigation_item)
      self.current_nav = navigation_item['sub']

    soup = self.follow_links(soup, baseurl, recursive=True)
    soup = self.sanitize_soup(soup, baseurl)
    return soup.prettify()

  def parse_soup(self, soup, filename, baseurl, output):
    old_nav = self.current_nav

    if self.layout == "TopShelf":
      result = self.parse_soup_topshelf(soup, filename, baseurl, output)
    else:
      result = self.parse_soup_raw(soup, filename, baseurl, output)

    self.current_nav = old_nav
    return result

  def follow_links(self, soup, baseurl, recursive=False):
    if self.recursion_limit and self.recursion_index > self.recursion_limit:
      accept_recursion = False
    else:
      accept_recursion = True
    for a in soup.findAll('a'):
      url = None
      try:
	url = urljoin(baseurl, a["href"])
      except: # No attribute href
	pass
      if url and url != baseurl:
	if recursive and accept_recursion:
	  self.recursion_index = self.recursion_index + 1
	  u = self.parse_url(url)
	  if u: a['href'] = "../%s" % u
	  self.recursion_index = self.recursion_index - 1
	else:
	  #u = self.get_url(url)
	  #if u: a['href'] = "../%s" % u
	  a['href'] = url
    return soup

  def sanitize_soup(self, soup, baseurl):

    allowed_head = ['title', 'link', 'meta']
    allowed_body = ['p', 'a', 'img', 'font', 'u', 'b', 'strong', 'i', 'em', 's', 'center', 'big', 'small', 'br', 'hr', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote']
    not_allowed_body = ['div', 'span', 'table', 'tr', 'th', 'td']
    allowed_body_attrs = {'a':['href', 'name', 'title'], 'img':['src', 'width', 'height', 'alt', 'align'], 'p':['align'], 'font':['size', 'color', 'face'], '*':['id', 'style', 'class']}
    not_allowed_body_attrs = {'img':['border']}
    remove_body = ['script']

    #
    # Extract anything but `allowed_head' from <head>
    #

    for head in soup.findAll('head'):
      #for base in head.findAll('base'):
      #  base.extract();
      for e in head.findAll():
	if e.__class__ == BeautifulSoup.Tag:
	  if e.name not in allowed_head:
	    e.extract()
	else:
	  e.extract()

    #
    # Modify <img src>
    #

    for img in soup.findAll('img'):
      url = urljoin(baseurl, img["src"])
      u = self.get_url(url, relative=os.path.dirname(self.translate_url_to_name(baseurl))+"/")
      if u: img['src'] = "%s" % u

    #
    # Remove `remove_body' tags from <body>
    # Filter `allowed_body' in <body>
    #

    for body in soup.findAll('body'):

      for unwanted in remove_body:
	for tag in soup.findAll(unwanted):
	  tag.extract()

      body.replaceWith(self.sanitize_soup_filter(soup, body, allowed_body, allowed_body_attrs, not_allowed_body, not_allowed_body_attrs, True));

    return soup


  def sanitize_soup_filter(self, parser, soup, allowed_tags, allowed_attrs, blacklist_tags, blacklist_attrs, keepSoup=False):

    if soup.__class__ != BeautifulSoup.Tag:
      return soup

    result = []
    for e in soup.contents:
      r = self.sanitize_soup_filter(parser, e, allowed_tags, allowed_attrs, blacklist_tags, blacklist_attrs)
      if type(r) == type([]): result.extend(r)
      else:                   result.append(r)

    if soup.name not in allowed_tags and not keepSoup:
      if soup.name not in blacklist_tags:
	print "extract <%s>" % soup.name
      return result

    else:

      if '*' not in allowed_attrs: allowed_attrs['*'] = []
      if soup.name not in allowed_attrs: allowed_attrs[soup.name] = []
      if '*' not in blacklist_attrs: blacklist_attrs['*'] = []
      if soup.name not in blacklist_attrs: blacklist_attrs[soup.name] = []

      #parser = soup
      #while parser.parent:
	#parser = parser.parent
      tag = BeautifulSoup.Tag(parser, soup.name)

      for attr, val in soup.attrs:
	if attr not in allowed_attrs[soup.name] and attr not in allowed_attrs['*']:
	  if attr not in blacklist_attrs[soup.name] and attr not in blacklist_attrs['*']:
	    print "extract <%s %s=\"%s\">" % (soup.name, attr, val)
	  #del soup[attr]
	else:
	  tag[attr] = val

      soup = tag

      for i in range(len(result)):
	soup.insert(i, result[i])
      #for e in soup:
	#if e not in result:
	  #e.extract()

      #i = 0
      #last = None
      #for e in result:
	#soup.insert(i, e)
	#i = i + 1
	#last = e
      #if last != None:
	#while last.nextSibling != None:
	  #last.nextSibling.extract()
      #else:
	#for e in soup.contents: e.extract()

      return soup

    #curr = soup.next
    #index = 0

    #while curr.nextSibling != None:
      #next = curr.nextSibling
      #if curr.__class__ == BeautifulSoup.Tag:
	#if curr.name not in allowed_tags:
	  #print "extract %s" % curr.name
	  #for e in curr:
	    #soup.insert(index, self.sanitize_soup_filter(e, allowed_tags))
	    #index = index + 1
	  #curr.extract()
	  #index = index - 1
	#else:
	  #curr.replaceWith(self.sanitize_soup_filter(curr, allowed_tags))
      #curr = next
      #index = index + 1

    #for center in soup.findAll('center'):
      #div = BeautifulSoup.Tag(soup, 'div')
      #div['style'] = 'display: block; margin-left: auto; margin-right: auto; text-align: center;';
      #for item in center.contents:
	#div.append(item)
      #center.replaceWith(div)
    #for font in soup.findAll('font'):
      #span = BeautifulSoup.Tag(soup, 'span')
      #style = []
      #try:
	#style.append("color: %s" % font['color'])
      #except:
	#pass
      #try:
	#style.append("font-family: %s" % font['face'])
      #except:
	#pass
      #try:
	#try:
	  #i = int(font['size'])
	  #if font['size'][0] == '+' or font['size'][0] == '-':
	    #if   i <= -6: style.append("font-size: 25%")
	    #elif i == -5: style.append("font-size: 33%")
	    #elif i == -4: style.append("font-size: 40%")
	    #elif i == -3: style.append("font-size: 57%")
	    #elif i == -2: style.append("font-size: 80%")
	    #elif i == -1: style.append("font-size: 91%")
	    #elif i ==  0: pass
	    #elif i ==  1: style.append("font-size: 110%")
	    #elif i ==  2: style.append("font-size: 125%")
	    #elif i ==  3: style.append("font-size: 175%")
	    #elif i ==  4: style.append("font-size: 250%")
	    #elif i ==  5: style.append("font-size: 300%")
	    #elif i >=  6: style.append("font-size: 400%")
	  #else:
	    #if   i <= 1: style.append("font-size: xx-small")
	    #elif i == 2: style.append("font-size: small")
	    #elif i == 3: style.append("font-size: medium")
	    #elif i == 4: style.append("font-size: large")
	    #elif i == 5: style.append("font-size: x-large")
	    #elif i >= 6: style.append("font-size: xx-large")
	#except:
	  ##style.append("font-size: %s" % font['size'])
	  #pass
      #except:
	#pass
      #span['style'] = "; ".join(style);
      #print "font: ", font
      #print "style: ", style
      #for item in font.contents:
	#span.append(item)
	#print "item: ", item
      #font.replaceWith(span)
      #print "span: ", span

    #return soup

  def set_metainfo(self, info, value):
    if   info == "title":	self.info_title = value
    elif info == "lang":	pass
    elif info == "ident":	self.info_url = value
    elif info == "subject":	self.info_tags = value
    elif info == "description":	pass
    elif info == "relation":	pass
    elif info == "creator":	self.info_author = value
    elif info == "publisher":	pass
    elif info == "date":	self.info_date = value
    elif info == "rights":	pass

  def get_metainfo(self, info):
    if   info == "title":	res = self.info_title.encode('utf-8')
    elif info == "lang":	res = "en"
    elif info == "ident":	res = self.info_url.encode('utf-8')
    elif info == "subject":	res = ", ".join(self.info_tags).encode('utf-8')
    elif info == "description":	res = ""
    elif info == "relation":	res = ""
    elif info == "creator":	res = self.info_author.decode('utf-8')
    elif info == "publisher":	res = ""
    elif info == "date":	res = self.info_date.strftime("%Y-%d-%dT%H:%M:%S+00:00")
    elif info == "rights":	res = ""
    if type(res) == str:
      res = res.decode('utf-8', 'replace')
    return res

  def soup_remove_before(self, soup, tag):
    while tag is not None and tag.name != 'body':
      after = tag.previousSibling
      while after is not None:
	ns = tag.previousSibling
	after.extract()
	after = ns
      tag = tag.parent

  def soup_remove_after(self, soup, tag):
    while tag is not None and tag.name != 'body':
      after = tag.nextSibling
      while after is not None:
	ns = tag.nextSibling
	after.extract()
	after = ns
      tag = tag.parent


help = """NAME

    topshelf -h
    topshelf [OPTIONS ...] [--] URL ...
    topshelf [--gui] (not yet implemented)

DESCRIPTION

    Download stories from BigCloset TopShelf and convert them to an epub e-book

    Version 0.1.3 (2009.12.09)

OPTIONS

    -h, --help
        This help message

    -c, --continue
        Continue even of there are errors downloading some files

    -r, --raw
        Raw pages (don't detect TopShelf BigCloset layout

    -d, --delete REGEXP
        Don't download url from this prefix (high priority)

    -a, --accept REGEXP
        Only download url from this prefix (low priority)

    -s, --skip
        Skip first page

    --replace SEARCH REPLACEMENT

    --gui
	Start the GUI (not yet implemented)

    -o OUTFILE
        use OUTFILE as filename for the resulting epub e-book

    -m METAINFO=VALUE
        set meta METAINFO to VALUE

SEE ALSO

    http://bigclosetr.us/topshelf/

""";

def main(argv):

  if not soup_ok:
    print "package beautifulSoup not found"
    return 1

  url = []
  obsoletes = []
  outfile = None
  layout = "TopShelf"
  accept = None
  delete = None
  skip = False
  show=False
  cont=False
  replace = []
  meta = {}
  i = 1
  argc = len(argv)
  while i < argc:
    arg = argv[i]
    if arg == "-o":
      i = i + 1
      outfile = argv[i]
    elif arg == "-h" or arg == "--help":
      print help
      return 0
    elif arg == "-r" or arg == "--raw":
      layout = None
    elif arg == "-c" or arg == "--continue":
      cont = True
    elif arg == "-s" or arg == "--skip":
      skip = True
    elif arg == "-a" or arg == "--accept":
      i = i + 1
      accept = argv[i]
    elif arg == "-d" or arg == "--delete":
      i = i + 1
      delete = argv[i]
    elif arg == "-m":
      i = i + 1
      m, eq, val = argv[i].partition("=")
      meta[m] = val.decode('utf-8')
    elif arg == "--replace":
      i = i + 1
      replace.append( (argv[i],argv[i+1]) )
      i = i + 1
    elif arg == "--show":
      show=True
    elif arg == "--":
      i = i + 1
      break
    else:
      break
    i = i + 1

  #if layout == "TopShelf" and not accept:
  #  accept = "bigclosetr\.us/topshelf/"

  for i in range(i, argc):
    url.append(argv[i])

  #remaining_args = argc - i
  #if remaining_args == 1:
  #  url = argv[i]
  #  i = i + 1
  #  remaining_args = remaining_args - 1
  #elif remaining_args >= 2:
  #  outfile = argv[i]
  #  url = argv[i+1]
  #  i = i + 2
  #  remaining_args = remaining_args - 2

  if not len(url):
    print "You should specify a URL"
    return 1

  for u in url:
    print "E-Book URL: %s" % u

  ts = TopShelf(layout=layout, accept_regexp=accept, delete_regexp=delete)
  ts.replace_show = False
  for m in meta:
    ts.set_metainfo(m, meta[m])
  for r1, r2 in replace:
    ts.init_replace(r1, r2, show);
  for u in url:
    ts.parse_url(u, output = not skip)

  if not outfile:
    author = make_filename(ts.info_author)
    title = make_filename(ts.info_title)
    if not title:
      title = os.path.basename(url[0])
    if author:
      #outfile = "%s-%s.epub" % (author, os.path.basename(url[0]))
      outfile = "%s-%s.epub" % (author, title)
      obsoletes.append("%s.epub" % os.path.basename(url[0]))
      obsoletes.append("%s-%s.epub" % (author, os.path.basename(url[0])))
    else:
      outfile = "%s.epub" % os.path.basename(url[0])

  if ts.error:
    print "Errors downloading E-Book: %s" % outfile
    if not cont: exit(1)
  else:
    print "Downloaded E-Book: %s" % outfile

  if len(obsoletes):
    f = open("obsolete.txt", "a")
    for o in obsoletes:
      f.write("%s\n" % o);
    f.close();

  #print ts.navigation
  ts.writeout(outfile)

try:
  import Tkinter as Tk
  import tkMessageBox
  import tkFileDialog
  gui_ok=True
except:
  gui_ok=False

class tk_gui:

  def run(self):
    self.clean()

    saveout = sys.stdout
    sys.stdout = self

    layout  = "TopShelf"
    accept  = None
    delete  = None
    skip    = self.var_skip == "yes"
    meta    = self.get_meta()
    outfile = None
    pattern = self.get_pattern()
    replace = self.get_replacement()
    show    = False

    if self.var_bcts.get() == "no": layout  = None
    if len(self.var_out.get()):     outfile = self.var_out.get()
    if len(self.var_accept.get()):  accept  = self.var_accept.get()
    if len(self.var_reject.get()):  delete  = self.var_reject.get()
    if len(self.var_title.get()):   meta['title']   = self.var_title.get()
    if len(self.var_creator.get()): meta['creator'] = self.var_creator.get()

    print "Layout:   %s" % repr(layout)
    print "Accept:   %s" % repr(accept)
    print "Delete:   %s" % repr(delete)
    print "Skip:     %s" % repr(skip)

    ts = TopShelf(layout=layout, accept_regexp=accept, delete_regexp=delete)
    ts.replace_show = False
    for m in meta:
      print "Meta:     %s=%s" % (repr(m), repr(meta[m]))
      ts.set_metainfo(m, meta[m])
    for i in range(min(len(pattern), len(replace))):
      if not len(pattern[i]): continue
      print "Replace:  %s -> %s" % (repr(pattern[i]), repr(replace[i]))
      ts.init_replace(pattern[i], replace[i], show);
    for u in self.get_url():
      print "Url:      %s" % (u)
      ts.parse_url(u, output = not skip)

    if not outfile:
      author = make_filename(ts.info_author)
      title = make_filename(ts.info_title)
      if not title:
	title = os.path.basename(url[0])
      if author:
	outfile = "%s-%s.epub" % (author, title)
      else:
	outfile = "%s.epub" % os.path.basename(url[0])

    print "Outfile:  %s" % outfile

    outfile = tkFileDialog.asksaveasfilename(defaultextension=".epub", initialfile=outfile)
    if outfile:
      print "Write in: %s" % outfile
      ts.writeout(outfile)
    else:
      print "Discard e-book"

    sys.stdout = saveout

  def write(self, s):
    self.text_log.insert(Tk.END, s)

  def clean(self):
    self.text_log.delete(1.0, Tk.END)

  def get_url(self):
    return self.get_text(self.text_url).split('\n')
  def get_meta(self):
    res = {}
    for m in self.get_text(self.text_url).split('\n'):
      a, _, b = m.partition('=')
      res[a] = b
    return res
  def get_pattern(self):
    return self.get_text(self.text_pattern).split('\n')
  def get_replacement(self):
    return self.get_text(self.text_replacement).split('\n')

  def get_text(self, text):
    str = text.get(1.0, Tk.END)
    return str.strip().replace("\r\n", "\n").replace("\r", "\n")

  def create_text(self, root):
    frame = Tk.Frame(root)

    sc_h = Tk.Scrollbar(frame, orient=Tk.HORIZONTAL)
    sc_h.grid(row=1, column=0, sticky=Tk.E+Tk.W)
    sc_v = Tk.Scrollbar(frame)
    sc_v.grid(row=0, column=1, sticky=Tk.N+Tk.S)

    text = Tk.Text(frame, wrap=Tk.NONE)
    text.grid(row=0, column=0, sticky=Tk.N+Tk.S+Tk.E+Tk.W)
    text.config(xscrollcommand=sc_h.set, yscrollcommand=sc_v.set)
    sc_h.config(command=text.xview)
    sc_v.config(command=text.yview)

    return frame, text

  def __init__(self, root):

    self.var_title   = Tk.StringVar()
    self.var_creator = Tk.StringVar()
    self.var_reject  = Tk.StringVar()
    self.var_accept  = Tk.StringVar()
    self.var_out     = Tk.StringVar()
    self.var_cont    = Tk.StringVar()
    self.var_bcts    = Tk.StringVar()
    self.var_skip    = Tk.StringVar()

    all = Tk.N+Tk.S+Tk.E+Tk.W

    frame_opt = Tk.Frame(root); frame_opt.grid(row=0, column=0, sticky=all)
    frame_btn = Tk.Frame(root); frame_btn.grid(row=2, column=0, sticky=all)

    text_log, self.text_log = self.create_text(root)
    self.text_log.config(height=10)
    text_log.grid(row=1, column=0, sticky=all)

    row = 0

    label = Tk.Label(frame_opt, text="URL (one per line)");
    label.grid(row=row, column=0, sticky=Tk.W)
    text_url, text_url_t = self.create_text(frame_opt)
    text_url_t.config(height=2, width=60)
    text_url.grid(row=row, column=1, columnspan=2, sticky=Tk.W+Tk.E)
    row+=1

    label = Tk.Label(frame_opt, text="Metadata");
    label.grid(row=row, column=0, sticky=Tk.W)
    text_meta, text_meta_t = self.create_text(frame_opt)
    text_meta_t.config(height=2, width=60)
    text_meta.grid(row=row, column=1, sticky=Tk.W+Tk.E)
    label = Tk.Label(frame_opt, text="(-m) auto detected\nUse name=value, one per line, epub name", justify=Tk.LEFT);
    label.grid(row=row, column=2, sticky=Tk.W)
    row+=1

    label = Tk.Label(frame_opt, text="Title");
    label.grid(row=row, column=0, sticky=Tk.W)
    entry_title = Tk.Entry(frame_opt, textvar=self.var_title)
    entry_title.grid(row=row, column=1, sticky=Tk.W+Tk.E)
    label = Tk.Label(frame_opt, text="(-m title=...) auto detected");
    label.grid(row=row, column=2, sticky=Tk.W)
    row+=1

    label = Tk.Label(frame_opt, text="Author");
    label.grid(row=row, column=0, sticky=Tk.W)
    entry_creator = Tk.Entry(frame_opt, textvar=self.var_creator)
    entry_creator.grid(row=row, column=1, sticky=Tk.W+Tk.E)
    label = Tk.Label(frame_opt, text="(-m creator=...) auto detected");
    label.grid(row=row, column=2, sticky=Tk.W)
    row+=1

    label = Tk.Label(frame_opt, text="Reject");
    label.grid(row=row, column=0, sticky=Tk.W)
    entry_delete = Tk.Entry(frame_opt, textvar=self.var_reject)
    entry_delete.grid(row=row, column=1, sticky=Tk.W+Tk.E)
    label = Tk.Label(frame_opt, text="(--delete)");
    label.grid(row=row, column=2, sticky=Tk.W)
    row+=1

    label = Tk.Label(frame_opt, text="Accept");
    label.grid(row=row, column=0, sticky=Tk.W)
    entry_accept = Tk.Entry(frame_opt, textvar=self.var_accept)
    entry_accept.grid(row=row, column=1, sticky=Tk.W+Tk.E)
    label = Tk.Label(frame_opt, text="(--accept)");
    label.grid(row=row, column=2, sticky=Tk.W)
    row+=1

    label = Tk.Label(frame_opt, text="Replace in HTML code");
    label.grid(row=row, column=0, sticky=Tk.W)
    frame_replace = Tk.Frame(frame_opt)
    frame_replace.grid(row=row, column=1, sticky=Tk.W+Tk.E)
    label = Tk.Label(frame_opt, text="(--replace)\nThe replacement text must match the pattern line by line", justify=Tk.LEFT);
    label.grid(row=row, column=2, sticky=Tk.W)
    label = Tk.Label(frame_replace, text="Pattern");
    label.grid(row=0, column=0, sticky=Tk.W)
    label = Tk.Label(frame_replace, text="Replacement");
    label.grid(row=0, column=1, sticky=Tk.W)
    text_pattern, text_pattern_t = self.create_text(frame_replace)
    text_pattern_t.config(height=2, width=30)
    text_pattern.grid(row=1, column=0, sticky=Tk.W+Tk.E)
    text_replacement, text_replacement_t = self.create_text(frame_replace)
    text_replacement_t.config(height=2, width=30)
    text_replacement.grid(row=1, column=1, sticky=Tk.W+Tk.E)
    row+=1

    label = Tk.Label(frame_opt, text="Force filename");
    label.grid(row=row, column=0, sticky=Tk.W)
    entry_output = Tk.Entry(frame_opt, textvar=self.var_out)
    entry_output.grid(row=row, column=1, sticky=Tk.W+Tk.E)
    label = Tk.Label(frame_opt, text="(-o)");
    label.grid(row=row, column=2, sticky=Tk.W)
    row+=1

    op_cont = Tk.Checkbutton(frame_opt, text="Ignore downloading errors (--continue)", onvalue="yes", offvalue="no", variable=self.var_cont)
    op_cont.grid(row=row, column=0, columnspan=3, sticky=Tk.W)
    row+=1
    op_bcts = Tk.Checkbutton(frame_opt, text="TopShelf BigCloset page (not --raw)", onvalue="yes", offvalue="no", variable=self.var_bcts)
    op_bcts.select()
    op_bcts.grid(row=row, column=0, columnspan=3, sticky=Tk.W)
    row+=1
    op_skip = Tk.Checkbutton(frame_opt, text="Skip the first page, only download linked pages (--skip)", onvalue="yes", offvalue="no", variable=self.var_skip)
    op_skip.grid(row=row, column=0, columnspan=3, sticky=Tk.W)
    row+=1

    button_close = Tk.Button(frame_btn, text="Close", command=root.quit)
    button_close.pack(side=Tk.RIGHT, fill=Tk.X)
    button_run   = Tk.Button(frame_btn, text="Run", command=self.run)
    button_run  .pack(side=Tk.RIGHT, fill=Tk.X)


    self.text_url         = text_url_t
    self.text_meta        = text_meta_t
    self.text_pattern     = text_pattern_t
    self.text_replacement = text_replacement_t



def gui():
  if not gui_ok:
    print "Tkinter not available"
    return 1
  if not soup_ok:
    tkMessageBox.showerror("Error", "Package BeautifulSoup not available")
    return 1
  root=Tk.Tk()
  tk_gui(root)
  root.mainloop()
  return 0

if __name__ == '__main__':
  if len(sys.argv) == 2 and sys.argv[1] == "--gui" or len(sys.argv) == 1:
    sys.exit(gui())
  else:
    sys.exit(main(sys.argv))

#######################################################################
## Copyright (c) 2009 Mildred Ki'Lya <mildred593(at)online.fr>
##
## Permission is hereby granted, free of charge, to any person
## obtaining a copy of this software and associated documentation
## files (the "Software"), to deal in the Software without
## restriction, including without limitation the rights to use,
## copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the
## Software is furnished to do so, subject to the following
## conditions:
##
## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
## OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
## HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
## WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
## FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
## OTHER DEALINGS IN THE SOFTWARE.
#######################################################################
## kate: hl Python; indent-width 2; space-indent on; replace-tabs off;
## kate: tab-width 8; remove-trailing-space on;
