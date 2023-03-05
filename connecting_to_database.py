from datetime import datetime
from typing import List
from datetime import date
from fastapi import FastAPI, Request, Depends
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


def get_problems(date):
    dt = datetime.strptime(date, '%Y-%m-%d')

    cursor.execute(
        'SELECT statement FROM Problems '
        'WHERE id IN (SELECT problem_id FROM Assignments WHERE problem_date = %s)',
        (dt.date(),)
    )

    # Fetch the results
    results = cursor.fetchall()

    return [row[0] for row in results]


@app.get("/")
def problems(request: Request):

    date = datetime.today().strftime('%Y-%m-%d')

    problems = get_problems(date)

    return templates.TemplateResponse("header.html", {"request": request, "problems": problems})


@app.on_event("shutdown")
def shutdown_event():
    cursor.close()
    connection.close()
