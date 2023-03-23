import logging
from datetime import datetime
from math import floor
from typing import Union
import pytz
import uvicorn
from fastapi import FastAPI, Request, Depends, Form, Response
from fastapi.templating import Jinja2Templates
import pymysql
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import HTTPException, status
from typing import Optional
from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
from pydantic import BaseModel
import socket
import hashlib
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import pymysql

#
if socket.gethostname() == 'myXPS':
    connection = pymysql.connect(
        host='localhost',
        user='ekatka',
        password='password',
        db='dailyAMC',
        port=3306
    )
else:
    connection = pymysql.connect(host=os.getenv("DATABASE_HOST"),
                                 port=3306,
                                 user=os.environ.get("DATABASE_USERNAME"),
                                 password=os.environ.get("DATABASE_PASSWORD"),
                                 database=os.environ.get("DATABASE"),
                                 )

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

SECRET_KEY = "0b407c2a4e151a402de0fe3f7cf77a91fa4da352f5ffcf547539632c26dec88e"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

cursor = connection.cursor()

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/templates", StaticFiles(directory="templates"), name="static")
security = HTTPBasic()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
if not os.environ.get('EMAIL_USER'):
    raise ("No email in env EMAIL_USER")
if not os.environ.get('EMAIL_PASSWORD'):
    raise ("No email in env EMAIL_PASSWORD")


#


class ExtendedOAuth2PasswordRequestForm(OAuth2PasswordRequestForm):
    remember_me: bool


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Union[str, None] = None


class User(BaseModel):
    email: Union[str, None] = None
    disabled: Union[bool, None] = None


class UserInDB(User):
    hashed_password: str


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(email: str):
    cursor = connection.cursor()
    query = "SELECT * FROM Users WHERE email = %s"
    cursor.execute(query, (email,))
    result = cursor.fetchone()
    cursor.close()
    if result:
        user_dict = {

            "email": result[1],
            "hashed_password": result[2]
        }
        return UserInDB(**user_dict)
    return None


def authenticate_user(email: str, password: str):
    user = get_user(email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(request: Request):
    access_token = request.cookies.get("access_token")
    # print(oauth2_scheme)
    # print(token)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return
        token_data = TokenData(email=email)
    except:
        return
    user = get_user(email=token_data.email)
    if user is None:
        return
    return user.email


def get_streak(user_id):
    cursor.execute(
        "SELECT Answers.is_correct, Assignments.problem_date FROM Answers INNER JOIN Assignments ON Answers.assigment_id=Assignments.problem_id WHERE Answers.user_id = %s ORDER BY Assignments.problem_date ASC",
        (user_id))
    results = cursor.fetchall()

    streak = 0
    current_date = None
    for row in results:
        answer_date = row[1]
        is_correct = bool(row[0])

        if is_correct:
            if current_date is None or answer_date == current_date + timedelta(days=1):
                streak += 1
                current_date = answer_date
            else:
                break
        else:
            streak = 0
            current_date = None

    return streak


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/login")
async def login(request: Request, form_data: ExtendedOAuth2PasswordRequestForm = Depends(), remember_me=Form(None)):
    email = form_data.username
    password = form_data.password

    logging.debug(f"User tries to login {email}")

    if remember_me == 'true':
        access_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    else:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expires = datetime.now(pytz.utc) + access_token_expires
    expires = expires.strftime("%Y-%m-%d %H:%M:%S")

    user_dict = authenticate_user(email, password)
    if not user_dict:
        error_message = "Incorrect email or password"
        return templates.TemplateResponse("login.html", {"request": request, "message_login": error_message})
        # raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": user_dict.email}, expires_delta=access_token_expires
    )

    redirect = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    redirect.set_cookie(key="access_token", value=access_token, expires=expires)
    return redirect


def get_solution_link():
    solution_query = 'SELECT original FROM Problems WHERE  id IN (SELECT problem_id FROM Assignments WHERE problem_date = %s)'
    date = datetime.today().strftime('%Y-%m-%d')
    cursor.execute(solution_query, (date))
    return cursor.fetchone()[0]


def get_problem_stats():
    date = datetime.today().strftime('%Y-%m-%d')
    cursor.execute("SELECT problem_id FROM Assignments WHERE problem_date = %s", (date))
    assignment_id = cursor.fetchone()[0]
    print(assignment_id, "assignment_id")

    cursor.execute("""
        SELECT COUNT(*)
        FROM Answers
        WHERE assigment_id = %s
    """, (assignment_id,))
    total_entries = cursor.fetchone()[0] + 1
    print(total_entries)

    cursor.execute("""
        SELECT COUNT(*)
        FROM Answers
        WHERE assigment_id = %s AND is_correct = 1
    """, (assignment_id,))
    correct_entries = cursor.fetchone()[0]
    print(correct_entries)

    percentage_correct = (correct_entries / total_entries) * 100
    return total_entries, floor(percentage_correct)


@app.post('/submit-answer')
async def get_answer(response: Response, request: Request, answer: str = Form(...),
                     current_user: Optional[str] = Depends(get_current_user)):
    date = datetime.today().strftime('%Y-%m-%d')
    # date = datetime.strptime(date, '%Y-%m-%d')
    correctnes_query = 'SELECT is_answer FROM Solutions WHERE  problem_id IN (SELECT problem_id FROM Assignments WHERE problem_date = %s) AND solution_text = %s'
    correct_answer = 'SELECT  solution_text FROM Solutions WHERE  problem_id IN (SELECT problem_id FROM Assignments WHERE problem_date = %s) AND is_answer = "1"'
    cursor.execute(correctnes_query, (date, answer))
    is_right = cursor.fetchone()[0]
    if is_right:
        streak = 1
    else:
        streak = 0
    # print(is_right, correct)
    cursor.execute(correct_answer, (date))
    correct = cursor.fetchone()[0]
    solutions = get_solutions(date)
    problems = get_problems(date)
    link_to_solution = get_solution_link()
    total = None
    stats_by_day = None
    total_solves = None
    percantage = None

    if current_user:

        print(total_solves, percantage)
        user = current_user
        print(user)
        get_user_id = 'SELECT id FROM Users WHERE email = %s'
        get_problem_id = 'SELECT problem_id FROM Assignments WHERE problem_date = %s'
        save_query = 'INSERT INTO Answers (user_id, assigment_id, is_correct, user_answer) VALUES (%s,%s,%s, %s)'

        cursor.execute(get_user_id, (user))
        user_id = cursor.fetchone()[0]
        print(user_id)
        cursor.execute(get_problem_id, (date))
        problem_id = cursor.fetchone()[0]
        print((type(user_id), type(problem_id), type(is_right)))
        values = ((user_id, problem_id, is_right, answer))
        cursor.execute(save_query, values)
        connection.commit()

        expire_time = datetime.now().replace(hour=23, minute=59, second=59) + timedelta(days=1)
        expire_time = expire_time.strftime("%Y-%m-%d %H:%M:%S")
        # response.set_cookie(key="is_right", value=is_right, expires=expire_time)
        streak = get_streak(user_id)
        total, stats_by_day = get_statistics(user_id)
        total_solves, percantage = get_problem_stats()
        is_login = True
        login = "Logout"
    else:
        is_login = False
        login = "Login"

    if is_right == 1:

        response = templates.TemplateResponse("correct.html",
                                              {"request": request, "problems": problems, "solutions": solutions,
                                               "correct": correct, "solution_link": link_to_solution,
                                               "is_login": is_login, "streak": streak, "True": True,
                                               "total_answer": total, "stats_by_day": stats_by_day, "login": login,
                                               "total_solves": total_solves, "percantage": percantage})
        # response.set_cookie(key="is_right", value=is_right, expires=expire_time)
        return response
    else:

        response = templates.TemplateResponse("wrong.html",
                                              {"request": request, "problems": problems, "solutions": solutions,
                                               "correct": correct, "answer": answer, "solution_link": link_to_solution,
                                               "is_login": is_login, "streak": streak, "True": True,
                                               "total_answer": total, "stats_by_day": stats_by_day, "login": login,
                                               "total_solves": total_solves, "percantage": percantage
                                               })
        # response.set_cookie(key="is_right", value=is_right, expires=expire_time)
        return response


def create_user(email, password):
    password_hash = get_password_hash(password)
    create_user_query = 'INSERT INTO Users(email, password_hash) VALUES (%s, %s)'
    cursor.execute(create_user_query, (email, password_hash))
    connection.commit()


@app.post("/signup")
async def sign_up(response: Response, request: Request, email: str = Form(...), password=Form(...),
                  password_again=Form(...)):
    message_signup = 0
    if get_user(email):
        message_signup = 'User already exists'
        # return {"message": "User already exists"}
    if password != password_again:
        message_signup = "Passwords don't match"
        # return {"message": "Passwords don't match"}
    if message_signup:
        return templates.TemplateResponse("login.html", {"request": request, "message_signup": message_signup})
    create_user(email, password)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expires = datetime.now(pytz.utc) + access_token_expires
    expires = expires.strftime("%Y-%m-%d %H:%M:%S")
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    access_token = create_access_token(
        data={"sub": email}, expires_delta=access_token_expires
    )
    response.set_cookie(key="access_token", value=access_token, expires=expires)

    return response


def get_problems(date):
    cursor.execute(
        'SELECT statement FROM Problems '
        'WHERE id IN (SELECT problem_id FROM Assignments WHERE problem_date = %s)',
        (date))

    results = cursor.fetchall()

    return [row[0] for row in results]


def get_solutions(date):
    cursor.execute('SELECT solution_text, id  FROM Solutions '
                   'WHERE problem_id IN (SELECT problem_id FROM Assignments WHERE problem_date = %s)',
                   date)
    results = cursor.fetchall()
    return [row[0] for row in results]


def get_user_id(current_user):
    id_query = 'SELECT id FROM Users WHERE email = %s'
    cursor.execute(id_query, (current_user))
    user_id = cursor.fetchone()[0]
    return user_id


def already_answered(current_user):
    date = datetime.today().strftime('%Y-%m-%d')
    user_id = get_user_id(current_user)
    answered = 'SELECT * FROM Answers INNER JOIN Assignments ON Answers.assigment_id = Assignments.problem_id WHERE Assignments.problem_date = %s AND Answers.user_id = %s'
    cursor.execute(answered, (date, user_id))
    if len(cursor.fetchall()) > 0:
        return True
    else:
        return False


def get_statistics(user_id):
    stats_by_day = {"Monday": {"correct": 0}, "Tuesday": {"correct": 0}, "Wednesday": {"correct": 0},
                    "Thursday": {"correct": 0}, "Friday": {"correct": 0}, "Saturday": {"correct": 0},
                    "Sunday": {"correct": 0}}
    total_correct = 0

    # Get the user's answers for all time

    sql = "SELECT a.is_correct, DAYNAME(s.problem_date) FROM Answers a JOIN Assignments s ON a.assigment_id = s.problem_id WHERE a.user_id = %s"
    cursor.execute(sql, (user_id))
    results = cursor.fetchall()

    # Update the statistics by weekday
    for result in results:
        if result[0] == 1:
            stats_by_day[result[1]]["correct"] += 1
            total_correct += 1
    return total_correct, stats_by_day


@app.get('/submit-answer')
async def get_answer(response: Response, request: Request,
                     current_user: Optional[str] = Depends(get_current_user)):
    date = datetime.today().strftime('%Y-%m-%d')
    user_id = get_user_id(current_user)
    correct_answer = 'SELECT  solution_text FROM Solutions WHERE  problem_id IN (SELECT problem_id FROM Assignments WHERE problem_date = %s) AND is_answer = "1"'
    user_answer_correct = 'SELECT is_correct, user_answer FROM Answers WHERE assigment_id IN (SELECT problem_id FROM Assignments WHERE problem_date = %s) AND user_id = %s'
    cursor.execute(user_answer_correct, (date, user_id))
    is_right, answer = cursor.fetchone()
    # answer = cursor.fetchone()[1]
    cursor.execute(correct_answer, (date))
    correct = cursor.fetchone()[0]
    solutions = get_solutions(date)
    problems = get_problems(date)
    link_to_solution = get_solution_link()
    is_login = True
    streak = get_streak(user_id)
    total, stats_by_day = get_statistics(user_id)
    total_solves, percantage = get_problem_stats()

    if is_right == 1:
        response = templates.TemplateResponse("correct.html",
                                              {"request": request, "problems": problems, "solutions": solutions,
                                               "correct": correct, "solution_link": link_to_solution,
                                               "is_login": is_login, "streak": streak, "True": True,
                                               "total_answers": total, "stats_by_day": stats_by_day,
                                               "login": "Logout", "total_solves": total_solves,
                                               "percantage": percantage})
        # response.set_cookie(key="is_right", value=is_right, expires=expire_time)
        return response
    else:
        response = templates.TemplateResponse("wrong.html",
                                              {"request": request, "problems": problems, "solutions": solutions,
                                               "correct": correct, "answer": answer, "solution_link": link_to_solution,
                                               "is_login": is_login, "streak": streak, "True": True,
                                               "total_answers": total, "stats_by_day": stats_by_day,
                                               "login": "Logout", "total_solves": total_solves,
                                               "percantage": percantage})
        # response.set_cookie(key="is_right", value=is_right, expires=expire_time)
        return response


@app.get("/")
def problems(response: Response, request: Request, current_user: Optional[str] = Depends(get_current_user)):
    # if "is_right" in request.cookies:
    #     redirect = RedirectResponse("/already_answered", status_code=status.HTTP_303_SEE_OTHER)
    #     return redirect
    login = 'Login'
    if current_user:
        already_answer = already_answered(current_user)
        login = 'Logout'
        if already_answer:
            # response.headers["Location"] = "/submit-answer"
            # response.status_code = 302
            response = RedirectResponse("/submit-answer", status_code=status.HTTP_303_SEE_OTHER)
            return response

    date = datetime.today().strftime('%Y-%m-%d')
    # date = datetime.strptime(date, '%Y-%m-%d')
    # print(date)
    problems = get_problems(date)
    solutions = get_solutions(date)
    user_text = "You are logged in"
    user = {"user": user_text} if current_user else {"user": "You are not logged in"}

    return templates.TemplateResponse("header.html",
                                      {"request": request, "problems": problems, "solutions": solutions, "login": login,
                                       **user}
                                      )


@app.post("/logout")
def logout(response: Response):
    try:
        response.delete_cookie("access_token")
        response.headers["Location"] = "/"
        response.status_code = 302
    except:
        return


@app.get("/about")
def about(request: Request, current_user: Optional[str] = Depends(get_current_user)):
    login = 'Login'
    if current_user:
        login = 'Logout'
    return templates.TemplateResponse("about.html", {"request": request, "login": login})


@app.get("/login")
async def login_page(request: Request, current_user: Optional[str] = Depends(get_current_user)):
    # if HTTPException:
    #     templates.TemplateResponse()
    if current_user:
        return templates.TemplateResponse("logout.html", {"request": request})
    else:
        return templates.TemplateResponse("login.html", {"request": request})


@app.on_event("shutdown")
def shutdown_event():
    cursor.close()
    connection.close()


def send_email(user, link):
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(os.environ['EMAIL_USER'], os.environ['EMAIL_PASSWORD'])
        msg = MIMEMultipart()
        msg['From'] = os.environ['EMAIL_USER']
        msg['To'] = user
        msg['Subject'] = "Password reset link"
        body = f"Please click on the link to reset your password: {link}"
        msg.attach(MIMEText(body, 'plain'))
        server.sendmail(os.environ['EMAIL_USER'], user, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


@app.post("/forgot-password")
async def forgot_password(request: Request, email: str = Form()):
    user = get_user(email)
    if user:
        cursor.execute("DESCRIBE Users")
        column_names = [column[0] for column in cursor.fetchall()]
        if "reset_token" not in column_names:
            # If the reset_token column doesn't exist, add it with varchar(50) data type
            cursor.execute("ALTER TABLE Users ADD COLUMN reset_token VARCHAR(50)")
            connection.commit()
        reset_token = str(uuid.uuid4())
        reset_link = f"localhost:8000/reset-password?token={reset_token}"
        cursor.execute("UPDATE Users SET reset_token=%s WHERE email=%s", (reset_token, email))

        connection.commit()

        if send_email(email, reset_link):
            return {"message": "Password link send successfully, check your email"}
        else:
            return {"message": "Error sending email. Please try again later."}
    else:
        raise HTTPException(status_code=400, detail="Email not found.")


@app.get("/forgot-password")
async def get_forgot_password(request: Request):
    return templates.TemplateResponse("reset_password.html", {"request": request})


@app.post("/reset-password")
async def reset_password(request: Request, token: str, password=Form(), password_again=Form()):
    message_signup = 0

    if password != password_again:
        message_signup = "Passwords don't match"

    if message_signup:
        return templates.TemplateResponse("new_password.html", {"request": request, "message_signup": message_signup})
    hash = get_password_hash(password)
    cursor.execute("UPDATE Users SET password_hash=%s, reset_token=NULL WHERE reset_token=%s", (hash, token))
    connection.commit()
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/reset-password")
async def serve_reset_password_page(request: Request, token: str):
    return templates.TemplateResponse("new_password.html", {"request": request, "token": token})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
