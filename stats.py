import glob, codecs, datetime
from bs4 import BeautifulSoup
from collections import Counter

def getAuthors(s):
  return s.find_all("author")

def getMonths(s):
  out = []
  for d in soup.find_all("date"):
    month = d.string.split("op ")[1].split(" ")[1]
    out.append(month)
  return out

fl = glob.glob("./f3ebdd81fe46ec766200a8b4dc749a758db0d066692ab250476d5a63/*.xml")

authors = []
dates = []

for f in fl:
  fin = codecs.open(f, "r", "utf-8")
  xml = fin.read()
  fin.close()

  soup = BeautifulSoup(xml)

  authors.extend(getAuthors(soup))
  dates.extend(getMonths(soup))

#for a in Counter(authors).most_common(10):
#  print a[0].string, a[1]

for d in Counter(dates).most_common(10):
  print d[0], d[1]


