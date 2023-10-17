import os
import dotenv
import requests
import json

def log(label, message):
    if type(message) is not str:
        message = json.dumps(message, default=lambda obj: obj.__dict__, indent=2)
    print(message)
    dotenv.load_dotenv()
    webhook_url = os.environ.get("DISCORD_HOOK")

    headers = {
        'Content-Type': 'application/json'
    }

    params = {
        "content": f"**{label}**\n```json\n{message}```"
    }

    response = requests.post(webhook_url, headers=headers, data=json.dumps(params))

    # Check the response status
    if response.status_code != 204:
        print(f"Failed to send message to Discord. Status code: {response.status_code}")
