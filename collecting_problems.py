from bs4 import BeautifulSoup  # library for working with html
from urllib.request import Request, urlopen, URLopener
import shutil
import mysql.connector
import os
import re


def test_insert():
    mydb = mysql.connector.connect(
        host="localhost",
        user="ekatka",
        password="password"
    )
    mycursor = mydb.cursor()
    mycursor.execute("USE dailyAMC;")
    mycursor.execute('select * from Problems')
    for x in mycursor:
        print(x)


def insert_problem_statement(statement, dif, origin, results, answer):
    mydb = mysql.connector.connect(
        host="localhost",
        user="ekatka",
        password="password"
    )
    mycursor = mydb.cursor()
    mycursor.execute("USE dailyAMC;")
    mysql_insert_problems = 'INSERT INTO Problems(statement, difficulty, original, answer) VALUES (%s, %s, %s, %s)'
    mycursor.execute(mysql_insert_problems, (statement, dif, origin, results[answer]))
    mycursor.execute('SET @last_problem_id =  LAST_INSERT_ID()')
    for ans in results:
        if results[ans] == results[answer]:
            is_ans = 1
        else:
            is_ans = 0
        mysql_insert_solutions = 'INSERT INTO Solutions(problem_id, solution_text, is_answer) VALUES (@last_problem_id, %s, %s)'
        mycursor.execute(mysql_insert_solutions, (results[ans], is_ans))
    mydb.commit()


def assign_difficulty(i):
    if i < 4:
        dif = 1
    elif i < 8:
        dif = 2
    elif i < 12:
        dif = 3
    elif i < 16:
        dif = 4
    elif i < 19:
        dif = 5
    elif i < 23:
        dif = 6
    else:
        dif = 7
    return dif




def make_answers(last_img, mode):
    if mode == 0:
        img_tag = last_img.find("img")
        text = img_tag["alt"]
    else:
        text = last_img["alt"]

    # print(text)
    matches = re.findall(r'\\textbf{\s*\(([A-Z])\)\s*}(.*?)\\qquad', text)
    matchE = re.findall(r'[E]\)\s*}(.*?)\$', text)
    # print(matchE)
    result = {letter: value for letter, value in matches}
    result['E'] = ''.join(matchE)
    return result


def get_soup(link):  # returns soup of whole page

    req = Request(  # getting the html
        url=link,
        headers={'User-Agent': 'Mozilla/5.0'}  # else throws 403
    )
    webpage = urlopen(req).read()
    soup = BeautifulSoup(webpage, "html.parser")
    return soup


def find_statement(line):  # extracts the whole statement from the html
    # problem_statement = [str(line)]
    # pattern = r'mathrm\s?\{\(A'
    pattern = r'textbf\s?\{\(A'
    look_next = 0
    if not len(re.findall(pattern, str(line))) == 0:
        look_next = 1
        img_tags = line.find_all('img')
        if img_tags:
            last_img = img_tags[-1]
            result = make_answers(last_img, 1)
            last_img.decompose()
        statement = [str(line)]

    else:
        statement = [str(line)]
        while look_next == 0:
            next_line = line.next_sibling
            if not len(re.findall(pattern, str(next_line))) == 0:
                look_next = 1
                result = make_answers(next_line, 0)

            else:
                statement.append(str(next_line))
                line = next_line
    return statement, result


def create_folder(problem_number):  # creates folder for each problem
    dir_name = str(year) + "_" + str(problem_number).zfill(2)
    os.mkdir(f"ProblemStatements/{dir_name}")
    # os.mkdir(f"ProblemStatements/{dir_name}/images")
    return dir_name


'''

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
        newPath = f"ProblemStatements/{dir_name}/images/{idx}.png"
        img["src"] = newPath

    return str(problem_soup)
'''


def replace_images(statement):
    asy_regex = r'\[asy\]'
    if len(re.findall(asy_regex, statement)) != 0:
        raise Exception
    regex = r"\\\[|\\\]"
    ProblemStatement = re.sub(regex, "$$", statement)
    img_regex = r'<img.*?alt="\s*\$(.*?)\$\s*".*?>'
    ProblemStatement = re.sub(img_regex, r"$\1$", ProblemStatement)
    return ProblemStatement


'''
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
'''

year = 2009



base_url = f"https://artofproblemsolving.com/wiki/index.php/{year}_AMC_12A_Problems/Problem_1"
answers_url = f"https://artofproblemsolving.com/wiki/index.php/{year}_AMC_12A_Answer_Key"

answer_soup = get_soup(answers_url)
answers = answer_soup.find_all('li')

for i in range(25):
    # print("run")
    try:
        new_number = str(i + 1)
        # dir_name = create_folder(new_number)

        try:
            dif = assign_difficulty(i + 1)
            pattern = re.compile(r'\d+$')
            new_url = pattern.sub(new_number, base_url)
            soup = get_soup(new_url)
            id_pattern = re.compile(r'Problem ?\d*')
            current_line = soup.find(id=id_pattern).parent.nextSibling.nextSibling
            problem_statement, results = find_statement(current_line)
            problem_statement = replace_images("\n".join(problem_statement))
            print(problem_statement)
            print(results)
            # save_images(problem_statement)
            # problem_statement = save_images(problem_statement)
            answer = answers[i].contents[0]
            insert_problem_statement(problem_statement, dif, new_url, results, answer)
            # save_statement(problem_statement)
            # answer = answers[i].contents[0]
            # save_answer(answer)


        except Exception as e:
            print(e)

            # shutil.rmtree(f"ProblemStatements/{dir_name}")

    except:
        pass
test_insert()
