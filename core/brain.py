import os
from gigachat import GigaChat
from dotenv import load_dotenv

load_dotenv()

client = GigaChat(
    credentials=os.getenv("GIGA_CREDENTIALS"),
    verify_ssl_certs=False
)


def ask_llm(prompt: str) -> str:

    response = client.chat({
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    })

    return response.choices[0].message.content