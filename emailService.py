from fastapi import FastAPI
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from starlette.requests import Request
from starlette.responses import JSONResponse
import dotenv
import os
from pydantic import BaseModel

dotenv.load_dotenv()
app = FastAPI()

conf = ConnectionConfig(
   MAIL_USERNAME = "bhushanmohol4@gmail.com",
   MAIL_PASSWORD = "nscbpvsxdbmkvgub",
   MAIL_FROM = "bhushanmohol4@gmail.com",
   MAIL_PORT = 587,
   MAIL_SERVER = "smtp.gmail.com",
   MAIL_STARTTLS = True,
   MAIL_SSL_TLS = False,
   USE_CREDENTIALS = True
)

class SendMailRequest(BaseModel):
    email_list: list[str]
    template: str

@app.post("/send_mail")
async def send_mail(req: SendMailRequest):
    message = MessageSchema(
        subject = "Fastapi-Mail module",
        recipients = req.email_list,
        body = req.template,
        subtype = "html"
        )

    fm = FastMail(conf)
    await fm.send_message(message)    

    return JSONResponse(status_code = 200, content = {"message": "email has been sent"})