from datetime import datetime, timedelta
from typing import Union
import pymysql
import pytz
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status, Form, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
from pydantic import Field

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "0b407c2a4e151a402de0fe3f7cf77a91fa4da352f5ffcf547539632c26dec88e"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

connection = pymysql.connect(
    host='localhost',
    user='ekatka',
    password='password',
    db='dailyAMC'
)
cursor = connection.cursor()


class ExtendedOAuth2PasswordRequestForm(OAuth2PasswordRequestForm):
    remember_me: bool = Field(default=False, alias="remember_me")


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


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/templates", StaticFiles(directory="templates"), name="static")


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
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = get_user(email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.post("/login")
async def login(response: Response, form_data: ExtendedOAuth2PasswordRequestForm = Depends()):
    email = form_data.username
    password = form_data.password
    remember_me = form_data.remember_me
    if remember_me:
        access_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    else:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    expires = datetime.now(pytz.utc) + access_token_expires
    expires = expires.strftime("%Y-%m-%d %H:%M:%S")

    user_dict = authenticate_user(email, password)
    if not user_dict:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": user_dict.email}, expires_delta=access_token_expires
    )
    response.set_cookie(key="access_token", value=access_token, expires=expires)

    return {"access_token": access_token, "token_type": "bearer"}


def create_user(email, password):
    password_hash = get_password_hash(password)
    create_user_query = 'INSERT INTO Users(email, password_hash) VALUES (%s, %s)'
    cursor.execute(create_user_query, (email, password_hash))
    connection.commit()


@app.post("/signup")
async def sign_up(response: Response, request: Request, email: str = Form(...), password=Form(...),
                  password_again=Form(...)):
    if get_user(email):
        return {"message": "user already exists"}
    if password != password_again:
        return {"message": "wrong password"}
    create_user(email, password)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expires = datetime.now(pytz.utc) + access_token_expires
    expires = expires.strftime("%Y-%m-%d %H:%M:%S")
    access_token = create_access_token(
        data={"sub": email}, expires_delta=access_token_expires
    )
    response.set_cookie(key="access_token", value=access_token, expires=expires)


@app.get("/login")
async def login_page(request: Request):
    print(request.cookies.get("access_token"))
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/users/me/")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return {"current_user": current_user}


@app.get("/users/me/items/")
async def read_own_items(current_user: User = Depends(get_current_active_user)):
    return {"item_id": "Foo", "owner": current_user.email}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
