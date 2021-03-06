################################################################################
# Script that scrapes a phpbb3 forum, assuming a three-layered depth:          
# give it the start of a forum, and it will fetch all subfora                  
# give it the start of a subforum, and it will fetch all the topics            
# give it the start of a topic, and it will fetch all the posts                
################################################################################

import urllib2, re, time, codecs, hashlib, os, httplib, glob, cgi
from bs4 import BeautifulSoup
from xml.sax.saxutils import escape

################################################################################
# TOOLS                                                                        #
################################################################################

def getHtml(url):
  content = ""
  try:
    req = urllib2.Request(url)
    req.add_header('User-agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; de;'+
      'rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5')
    resp = urllib2.urlopen(req)
    content = resp.read()
  except:
    print "url", url, "not working"
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

def writeOut(posts, foldername):
  """ write out a portion of the posts to a file """
  xml = "<posts>\n"
  pids = []
  for post in posts:
    pid = post["pid"]
    if pid not in pids:
      xml = xml + xmlify_post(post)
      pids.append(pid)
  xml = xml + "</posts>"
  fname = hashlib.sha224(xml.encode("utf-8")).hexdigest()
  print "\twriting to file:", foldername + "/" + fname
  fout = codecs.open("./" + foldername + "/" + fname + ".xml", "w", "utf-8")
  fout.write(xml)
  fout.close()

def getDownloadedTopicIDs(foldername):
  fl = glob.glob("./" + foldername + "/*.xml")
  regex = re.compile("<topicid>(.+?)</topicid>")
  out = []
  for f in fl:
    fin = codecs.open(f, "r", "utf-8")
    xml = fin.read()
    fin.close()
    out.extend(regex.findall(xml))
  return list(set(out))

def getForumAndTopicName(html):
  """ from a page from a topic, fetch the forum and topic name """
  try:
    soup = BeautifulSoup(html, "html5lib")
    forumname = soup.find("fieldset", "jumpbox").find("option", 
                          attrs={"selected": "selected"}).text.strip()
    topicname = soup.find("h3", "first").find("a").text
    return forumname, topicname
  except:
    return "", ""

################################################################################
# DEAL WITH INDIVIDUAL POSTS                                                   #
################################################################################

def getPostDivs(html):
  """ get divs in html that contain individual posts """
  try:
    soup = BeautifulSoup(html, "html5lib")
    return soup.find_all("div", "postbody")
  except:
    return []

def getStructuredData(post, base, url, forum, topic):
  """ get postid, author, date and content from post html """
  try:
    content = getContent(post)
    postid = getPostId(post)
    author = getAuthor(post)
    date = getDate(post)
    out = {"id": postid, "author": author, "date": date, "content": content,
            "forumid": forum, "topicid": topic, "base": base, "url": url}
    return out
  except:
    print "\t\terror in fetching single post, probably nothing majorly wrong"
    return {}

def getProfileData(html, pid):
  """ get author profile data for post """
  out = {}
  soup = BeautifulSoup(html, "html5lib")
  pdataraw = soup.find("dl", attrs={"class": "postprofile", 
                                    "id": "profile" + pid.lstrip("p")})
  try:
    dds = pdataraw.find_all("dd")
    for dd in dds:
      try:
        regexkey = re.compile("<strong>(.+)</strong>")
        regexvalue = re.compile("</strong>(.+)</dd>")
        key = regexkey.findall(unicode(dd))[0].strip().rstrip(":").lower()
        value = regexvalue.findall(unicode(dd))[0].strip()
        out[key] = value
      except IndexError:
        continue
  except:
    out = out
  return out

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
  print "\tfetching posts from topic", url
  pages_with_topic = getPagesFromTopic(base, url)
  posts = []
  for page_url in pages_with_topic:
    posts_from_page = getPostsFromPage(base, page_url)
    posts.extend(posts_from_page)
  return posts

def getPostsFromPage(base, url):
  """ from a single page with post, extract the posts structured """
  out = []
  forum = re.compile("f=(\d+?)&").findall(url)[0]
  topic = re.compile("t=(\d+?)&").findall(url)[0]
  fullurl = base + url.lstrip(".")
  html = getHtml(fullurl)
  (forumname, topicname) = getForumAndTopicName(html)
  posts = getPostDivs(html)
  for post in posts:
    structdata = getStructuredData(post, base, url, forum, topic)
    if structdata:
      uniqueid = fullurl + structdata["id"]
      pid = hashlib.sha224(uniqueid.encode("utf-8")).hexdigest()
      structdata["pid"] = pid
      structdata["forumname"] = forumname
      structdata["topicname"] = topicname
      profiledata = getProfileData(html, structdata["id"])
      for key in profiledata.keys():
        structdata[key] = profiledata[key]
      out.append(structdata)
  return out

def getPagesFromTopic(base, url):
  """ from the start page of a topic, get all the pages for that topic """
  # might need to be changed to look like getPagesFromForum
  out = [url]
  html = getHtml(base + url.lstrip("."))
  try:
    soup = BeautifulSoup(html, "html5lib")
    hrefs = soup.find("div", "pagination").find_all("a")
    for href in hrefs:
      if url in href.get("href"):
        last_href = href.get("href")
    # get start number from last_href
    regex = re.compile("start=(\d+)")
    try:
      final_start = int(regex.findall(last_href)[0])
    except:
      final_start = -1
    extra_url = url + "&start="
    extra_start = 20 # assume the increment is 20
    while extra_start < final_start:
      out.append(extra_url + str(extra_start))
      extra_start += 20
    if final_start > 0:
      out.append(extra_url + str(final_start))
    return out
  except:
    return out

################################################################################
# RETRIEVE TOPICS FROM SUBFORUM                                                #
################################################################################

def getTopicsFromSubforum(base, url):
  """ go through the topic pages of a forum and then gather all the topics
      via the step of gathering all the pages in the subforum """
  print "fetching the topics from subforum", url
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
    soup = BeautifulSoup(html, "html5lib")
    topicas = soup.find_all("a", "topictitle")
    for topica in topicas:
      out.append(topica.get("href"))
    return out
  
def getPagesFromSubforum(base, url):
  """ from the start page in a forum, get the links to all the pages """
  out = [url.lstrip(".")]
  html = getHtml(base + url.lstrip("."))
  soup = BeautifulSoup(html, "html5lib")
  try:
    hrefs = soup.find("div", "pagination").find_all("a")
  except:
    hrefs = []
  last_href = ""
  for href in hrefs:
    if "viewforum.php" in href.get("href"):
      last_href = href.get("href")
  # get start number from last_href
  regex = re.compile("start=(\d+)")
  try:
    final_start = int(regex.findall(last_href)[0])
  except:
    final_start = -1
  extra_url = url + "&start="
  extra_start = 20 # assume the increment is 20
  while extra_start < final_start:
    out.append(extra_url + str(extra_start))
    extra_start += 20
  if final_start > 0:
    out.append(extra_url + str(final_start))
  return out

################################################################################
# RETRIEVE SUBFORA FROM FORUM                                                  #
################################################################################

def getSubforaFromForum(url):
  out = []
  html = getHtml(url)
  soup = BeautifulSoup(html, "html5lib")
  hrefs = soup.find_all("a", "forumtitle")
  for href in hrefs:
    out.append(href.get("href"))
  return out

################################################################################
# MAIN METHOD                                                                  #
################################################################################

def main():
  base_url = "http://www.userbase.be/forum"

  foldername = hashlib.sha224(base_url.encode("utf-8")).hexdigest()
  downloaded = []
  try:
    os.mkdir("./" + foldername)
  except OSError:
    print "foldername for this forum exists already"
    downloaded = getDownloadedTopicIDs(foldername)
  subfora_from_forum = getSubforaFromForum(base_url)
  posts = []
  for subforum_url in subfora_from_forum:
    topics_from_subforum = getTopicsFromSubforum(base_url, subforum_url)
    for topic_url in topics_from_subforum:
      regex = re.compile("t=(\d+?)&")
      topic_id = regex.findall(topic_url)[0]
      if topic_id not in downloaded:
        posts.extend(getPostsFromTopic(base_url, topic_url))
        if len(posts) >= 50:
          writeOut(posts, foldername)
          posts = []
    writeOut(posts, foldername)

if __name__ == "__main__":
    main()
