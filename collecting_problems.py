from bs4 import BeautifulSoup  # library for working with html
from urllib.request import Request, urlopen, URLopener
import shutil

import os
import re


def get_soup(link):  # returns soup of whole page

    req = Request(  # getting the html
        url=link,
        headers={'User-Agent': 'Mozilla/5.0'}  # else throws 403
    )
    webpage = urlopen(req).read()
    soup = BeautifulSoup(webpage, "html.parser")
    return soup


def find_statement(line):  # extracts the whole statement from the html
    problem_statement = [str(line)]
    # pattern = r'mathrm\s?\{\(A'
    pattern = r'textbf\s?\{\(A'
    while len(re.findall(pattern, str(line))) == 0:
        next_line = line.next_sibling
        problem_statement.append(str(next_line))
        line = next_line
    return problem_statement


def create_photo_folder(problem_number):  # creates folder for each problem
    dir_name = str(year) + "_" + str(problem_number).zfill(2)
    os.mkdir(f"ProblemStatements/{dir_name}")
    os.mkdir(f"ProblemStatements/{dir_name}/images")
    return dir_name

def save_images(statement):
    problem_soup = BeautifulSoup(statement, 'html.parser')
    img_tags = problem_soup.find_all('img')
    urls = [img['src'] for img in img_tags]

    opener = URLopener()
    opener.addheader('User-Agent', 'Mozilla/5.0')

    for idx, url in enumerate(urls):
        url = url.replace("//", "http://")
        filename, headers = opener.retrieve(url, f"ProblemStatements/{dir_name}/images/{idx}.png")

    for idx, img in enumerate(img_tags):
        newPath = f"{dir_name}/images/{idx}.png"
        img["src"] = newPath

    return str(problem_soup)

def save_statement(statement):
    problem = open(f"ProblemStatements/{dir_name}/ProblemStatement.html", "w")
    problem.write(statement)
    problem.close()

def save_answer(answer):
    answer_file = open(f"ProblemStatements/{dir_name}/answer.txt", "w")
    answer_file.write(answer)
    answer_file.close()
    link_file = open(f"ProblemStatements/{dir_name}/solution.txt", "w")
    link_file.write(new_url)
    link_file.close()

year = 2011


base_url = f"https://artofproblemsolving.com/wiki/index.php/{year}_AMC_12A_Problems/Problem_1"
answers_url = f"https://artofproblemsolving.com/wiki/index.php/{year}_AMC_12A_Answer_Key"

answer_soup = get_soup(answers_url)
answers = answer_soup.find_all('li')


for i in range(25):
    try:
        new_number = str(i + 1)
        dir_name = create_photo_folder(new_number)

        try:
            pattern = re.compile(r'\d+$')
            new_url = pattern.sub(new_number, base_url)
            soup = get_soup(new_url)
            id_pattern = re.compile(r'Problem ?\d*')
            current_line = soup.find(id=id_pattern).parent.nextSibling.nextSibling
            problem_statement = "\n".join(find_statement(current_line))
            save_images(problem_statement)
            problem_statement = save_images(problem_statement)
            save_statement(problem_statement)
            answer = answers[i].contents[0]
            save_answer(answer)
        except:

            shutil.rmtree(f"ProblemStatements/{dir_name}")

    except:
        pass