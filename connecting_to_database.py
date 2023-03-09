from datetime import datetime
from typing import List
from datetime import date
from fastapi import FastAPI, Request, Depends, Form
from fastapi.templating import Jinja2Templates
import pymysql

connection = pymysql.connect(
    host='localhost',
    user='ekatka',
    password='',
    db='dailyAMC'
)

cursor = connection.cursor()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def get_solution_link():
    solution_query = 'SELECT original FROM Problems WHERE  id IN (SELECT problem_id FROM Assignments WHERE problem_date = %s)'
    date = datetime.today().strftime('%Y-%m-%d')
    cursor.execute(solution_query, (date))
    return cursor.fetchone()[0]
@app.post('/submit-answer')
async def get_answer(request: Request, answer: str = Form(...)):
    date = datetime.today().strftime('%Y-%m-%d')
    # date = datetime.strptime(date, '%Y-%m-%d')
    correctnes_query = 'SELECT is_answer FROM Solutions WHERE  problem_id IN (SELECT problem_id FROM Assignments WHERE problem_date = %s) AND solution_text = %s'
    correct_answer =  'SELECT  solution_text FROM Solutions WHERE  problem_id IN (SELECT problem_id FROM Assignments WHERE problem_date = %s) AND is_answer = "1"'
    cursor.execute(correctnes_query, (date, answer))
    is_right = cursor.fetchone()[0]
    # print(is_right, correct)
    cursor.execute(correct_answer, (date))
    correct = cursor.fetchone()[0]
    solutions = get_solutions(date)
    problems = get_problems(date)
    link_to_solution = get_solution_link()

    if is_right == 1:
        return templates.TemplateResponse("correct.html",
                                          {"request": request, "problems": problems, "solutions": solutions,
                                           "correct": correct, "solution_link": link_to_solution})
    else:
        return templates.TemplateResponse("wrong.html",
                                          {"request": request, "problems": problems, "solutions": solutions,
                                           "correct": correct, "answer": answer, "solution_link": link_to_solution})


def get_problems(date):
    # Convert the date string to a datetime object

    cursor.execute(
        'SELECT statement FROM Problems '
        'WHERE id IN (SELECT problem_id FROM Assignments WHERE problem_date = %s)',
        date
    )

    # Fetch the results
    results = cursor.fetchall()

    return [row[0] for row in results]


def get_solutions(date):
    cursor.execute('SELECT solution_text, id  FROM Solutions '
                   'WHERE problem_id IN (SELECT problem_id FROM Assignments WHERE problem_date = %s)',
                   date)
    results = cursor.fetchall()
    return [row[0] for row in results]


@app.get("/")
def problems(request: Request):
    date = datetime.today().strftime('%Y-%m-%d')
    # date = datetime.strptime(date, '%Y-%m-%d')
    # print(date)
    problems = get_problems(date)
    solutions = get_solutions(date)

    return templates.TemplateResponse("header.html", {"request": request, "problems": problems, "solutions": solutions}
                                      )


@app.on_event("shutdown")
def shutdown_event():
    cursor.close()
    connection.close()
