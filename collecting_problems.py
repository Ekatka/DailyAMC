from bs4 import BeautifulSoup  # library for working with html
from urllib.request import Request, urlopen

# working with urls

currentUrl = "https://artofproblemsolving.com/wiki/index.php/2020_AMC_12A_Problems/Problem_1"  # later will change last number in problem

req = Request(  # getting the html
    url=currentUrl,
    headers={'User-Agent': 'Mozilla/5.0'}  # else throws 403
)
webpage = urlopen(req).read()
soup = BeautifulSoup(webpage, "html.parser")

problemHTML = '<span class="mw-headline" id="Problem">Problem</span>'
problemTitle = soup.find(id="Problem")
print(soup.find(id="Problem").parent.next_sibling)
