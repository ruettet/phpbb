################################################################################
# Script that scrapes a phpbb3 forum, assuming a three-layered depth:          
# give it the start of a forum, and it will fetch all subfora                  
# give it the start of a subforum, and it will fetch all the topics            
# give it the start of a topic, and it will fetch all the posts                
# TODO
# - get subfora from forum
# - continuation: if the script stops, it has to restart at the position where
#   it left off
# - standoff the xml generation to a separate method
################################################################################

import urllib2, re, time, codecs
from bs4 import BeautifulSoup
from xml.sax.saxutils import escape

################################################################################
# TOOLS                                                                        #
################################################################################

def getHtml(url):
  req = urllib2.Request(url)
  req.add_header('User-agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; de;' + 
    'rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5')
  resp = urllib2.urlopen(req)
  content = resp.read()
  addURL(url)
  return content

def xmlify_post(sd):
  """ transform a structured post object into xml """
  nodes = ["\t<post>"]
  for key in sd.keys():
    value = sd[key]
    s = "\t\t<" + key + ">" + escape(value) + "</" + key + ">"
    nodes.append(s)
  nodes.append("\t</post>\n")
  return "\n".join(nodes)

################################################################################
# DEAL WITH INDIVIDUAL POSTS                                                   #
################################################################################

def getPostDivs(html):
  """ get divs in html that contain individual posts """
  soup = BeautifulSoup(html)
  return soup.find_all("div", "postbody")

def getStructuredData(post, base, url, forum, topic):
  """ get postid, author, date and content from post html """
  content = getContent(post)
  postid = getPostId(post)
  author = getAuthor(post)
  date = getDate(post)
  return {"id": postid, "author": author, "date": date, "content": content,
          "forumid": forum, "topicid": topic, "base": base, "forumurl": url}

def getAuthor(post):
  """ get author from post """
  return post.find_all(href=re.compile("memberlist"))[-1].get_text()

def getDate(post):
  """ get unparsed data from post """
  regex = re.compile("[^\w\s:]")
  text = re.sub(regex, "", post.find("p", "author").get_text())
  return text.split(getAuthor(post))[-1].strip()

def getPostId(post):
  """ get id from post """
  return post.find("h3").find("a").get("href").strip("#")

def getContent(post):
  """ get content from post """
  try:
    return post.find("div", "content").get_text()
  except AttributeError:
    return "NA"

################################################################################
# RETRIEVE POSTS FROM TOPICS                                                   #
################################################################################

def getPostsFromTopic(base, url):
  """ wrapper that will fetch all posts from a topic via a subroutine that
      fetches all the pages for that topic """
  print "fetching posts from topic", base, url
  pages_with_topic = getPagesFromTopic(base, url)
  for page_url in pages_with_topic:
    posts_from_page = getPostsFromPage(base, url)
  return posts_from_page

def getPostsFromPage(base, url):
  """ from a single page with post, extract the posts structured """
  out = []
  forum = re.compile("f=(\d.+?)&").findall(url)[0]
  topic = re.compile("t=(\d.+?)&").findall(url)[0]
  fullurl = base + url.lstrip(".")
  html = getHtml(fullurl)
  posts = getPostDivs(html)
  for post in posts:
    structdate = getStructuredData(post, base, url, forum, topic)
    out.append(structdate)
  return out

def getPagesFromTopic(base, url):
  """ from the start page of a topic, get all the pages for that topic """
  # might need to be changed to look like getPagesFromForum
  out = [url]
  html = getHtml(base + url.lstrip("."))
  soup = BeautifulSoup(html)
  hrefs = soup.find("div", "pagination").find_all("a")
  for href in hrefs:
    if "viewtopic.php" in href.get("href"):
      out.append(href.get("href"))
  return out

################################################################################
# RETRIEVE TOPICS FROM SUBFORUM                                                #
################################################################################

def getTopicsFromSubforum(base, url):
  """ go through the topic pages of a forum and then gather all the topics
      via the step of gathering all the pages in the subforum """
  print "fetching the topics from subforum", base, url
  out = []
  page_urls_in_subforum = getPagesFromSubforum(base, url)
  for page_url in page_urls_in_subforum:
    topics = getTopicsFromSubforumpage(base, page_url)
    out.extend(topics)
  return out

def getTopicsFromSubforumpage(base, url):
    """ from a single page with topics in a subforum, get the topic links """
    out = []
    html = getHtml(base + url.lstrip("."))
    soup = BeautifulSoup(html)
    topicas = soup.find_all("a", "topictitle")
    for topica in topicas:
      out.append(topica.get("href"))
    return out
  
def getPagesFromSubforum(base, url):
  """ from the start page in a forum, get the links to all the pages """
  out = [url.lstrip(".")]
  html = getHtml(base + url.lstrip("."))
  soup = BeautifulSoup(html)
  hrefs = soup.find("div", "pagination").find_all("a")
  last_href = ""
  for href in hrefs:
    if "viewforum.php" in href.get("href"):
      last_href = href.get("href")
  # get start number from last_href
  regex = re.compile("start=(\d+)")
  final_start = int(regex.findall(last_href)[0])
  extra_url = url.lstrip(".") + "&start="
  extra_start = 50 # assume the increment is 50
  while extra_start < final_start:
    out.append(extra_url + str(extra_start))
    extra_start += 50
  out.append(extra_url + str(final_start))
  return out

################################################################################
# RETRIEVE SUBFORA FROM FORUM                                                  #
################################################################################

def getSubforaFromForum(url):
  return ["./viewforum.php?f=77"]

################################################################################
# MAIN METHOD                                                                  #
################################################################################

def main():
  xml = "<posts>\n"
  base_url = "http://userbase.be/forum"
  subfora_from_forum = getSubforaFromForum(base_url)
  for subforum_url in subfora_from_forum:
    topics_from_subforum = getTopicsFromSubforum(base_url, subforum_url)
    for topic_url in topics_from_subforum[0:10]:
      posts = getPostsFromTopic(base_url, topic_url)
      for post in posts:
        xml = xml + xmlify_post(post)
  xml = xml + "<posts>"
  fout = codecs.open("out.xml", "w", "utf-8")
  fout.write(xml)
  fout.close()

if __name__ == "__main__":
    main()
