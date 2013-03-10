import urllib2, re, time, codecs
from bs4 import BeautifulSoup
from xml.sax.saxutils import escape

def getHtml(url):
  """ get html from url """
  req = urllib2.Request(url)
  req.add_header('User-agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; de;' + 
    'rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5')
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
  """ get author from post """
  return post.find_all(href=re.compile("memberlist"))[-1].get_text()

def getDate(post):
  """ get unparsed data from post """
  regex = re.compile("[^\w\s:]")
  text = re.sub(regex, "", post.find("p", "author").get_text()
  return text.split(getAuthor(post))[-1]).strip()

def getPostId(post):
  """ get id from post """
  return post.find("h3").find("a").get("href").strip("#")

def getContent(post):
  """ get content from post """
  return post.find("div", "content").get_text()

def xmlify(sd):
  """ transform a structured post object into xml """
  nodes = ["<post>"]
  for key in sd.keys():
    value = sd[key]
    s = "<" + key + ">" + escape(value) + "</" + key + ">"
    nodes.append(s)
  nodes.append("</post>")
  return "\n".join(nodes)

def getPostsFromPage(base, url):
  """ from a single page with post, extract the posts structured """
  out = []
  fullurl = base + url.lstrip(".")
  html = getHtml(fullurl)
  posts = getPostDivs(html)
  for post in posts:
    structdate = getStructuredData(post)
    out.append(structdate)
  return out

def getPagesFromTopic(base, url):
  """ from the start page of a topic, get all the pages for that topic """
  out = [url]
  html = getHtml(base + url.lstrip("."))
  soup = BeautifulSoup(html)
  hrefs = soup.find("div", "pagination").find_all("a")
  for href in hrefs:
    if "viewtopic.php" in href.get("href"):
      out.append(href.get("href"))
  return out

base_url = "http://userbase.be/forum"
topics_from_forum = ["./viewtopic.php?f=77&t=35417"]
for topic_url in topics_from_forum:
	pages_with_topic = getPagesFromTopic(base_url, topic_url)
	for page_url in pages_with_topic:
		posts_from_page = getPostsFromPage(base_url, page_url)
		print posts_from_page

