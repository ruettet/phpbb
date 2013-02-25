import urllib2, re, time, codecs
from bs4 import BeautifulSoup
from xml.sax.saxutils import escape

def getHtml(url):
  """ get html from url """
  req = urllib2.Request(url)
  req.add_header('User-agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5')
  resp = urllib2.urlopen(req)
  content = resp.read()
  return content

def getPostDivs(html):
  """ get divs in html that contain individual posts """
  soup = BeautifulSoup(html)
  return soup.find_all("div", "postbody")

def getStructuredData(post):
  """ get postid, author, date and content from post html """
  content = getContent(post)
  postid = getPostId(post)
  author = getAuthor(post)
  date = getDate(post)
  return {"id": postid, "author": author, "date": date, "content": content}

def getAuthor(post):
  return post.find_all(href=re.compile("memberlist"))[-1].get_text()

def getDate(post):
  regex = re.compile("[^\w\s:]")
  return re.sub(regex, "", post.find("p", "author").get_text().split(getAuthor(post))[-1]).strip()

def getPostId(post):
  return post.find("h3").find("a").get("href").strip("#")

def getContent(post):
  return post.find("div", "content").get_text()

def xmlify(sd):
  nodes = ["<post>"]
  for key in sd.keys():
    value = sd[key]
    s = "<" + key + ">" + escape(value) + "</" + key + ">"
    nodes.append(s)
  nodes.append("</post>")
  return "\n".join(nodes)

def getPostsFromPage(url):
  xmlout = []
  html = getHtml(url)
  posts = getPostDivs(html)
  for post in posts:
    structdate = getStructuredData(post)
    xmlout.append(xmlify(structdate))
  return "\n".join(xmlout)

xml = ["<?xml version=\"1.0\"?>"]
xml.append("<posts>")
page_with_posts = "http://userbase.be/forum/viewtopic.php?f=77&t=35834"
xml.append(getPostsFromPage(page_with_posts))
xml.append("</posts>")

fout = codecs.open("text.xml", "w", "utf-8")
fout.write( "\n".join(xml) )
fout.close()
