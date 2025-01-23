from random import choice
from os import getcwd
from os.path import join

from yaml import safe_load
from fastapi import FastAPI, Request, HTTPException

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from openai import OpenAI

# Load configuration
config_path = join(getcwd(), "config.yaml")
with open(config_path, "r") as config_file:
    config = safe_load(config_file)

# LINE Messaging API config
line_channel_access_token = config["line"]["channel_access_token"]
line_channel_secret = config["line"]["channel_secret"]
line_bot_api = LineBotApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)

# OpenAI config
openai_base_url = config["openai"]["base_url"]
openai_api_key = config["openai"]["api_key"]
openai_model = config["openai"]["model"]
openai_client = OpenAI(
    base_url=openai_base_url,
    api_key=openai_api_key,
)

# Flask config
app = FastAPI()


# Callback endpoint
@app.post("/callback")
async def callback(request: Request):
    # get X-Line-Signature header value
    signature = request.headers["X-Line-Signature"]

    # get request body as text
    body = await request.body()
    body = body.decode("utf-8")

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError as e:
        raise HTTPException(400, e.message)

    return "OK"


# Message event handler
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # Ignore non-text-message event
    if not isinstance(event.message, TextMessage):
        return

    # Get text from the message
    user_text = event.message.text

    # Generate completion using OpenAI
    completion = openai_client.chat.completions.create(
        model=openai_model,
        messages=[
            {
                "role": "system",
                "content": "You are a assistant.",
            },
            {
                "role": "user",
                "content": user_text,
            },
        ],
    )

    # Extract the completion from OpenAI
    completion_choice = choice(completion.choices)
    completion_content = completion_choice.message.content

    # Check completion
    if not completion_content:
        return

    # Reply to the user with the generated response
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=completion_content.strip()),
    )
