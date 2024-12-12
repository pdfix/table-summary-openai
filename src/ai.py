import base64

import httpx
from openai import OpenAI


# Function to encode the image
def encode_image(image_path: str):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def table_summary(img_path: str, api_key: str, lang: str):
    # Getting the base64 string
    base64_image = encode_image(img_path)

    client = OpenAI(
        api_key=api_key, timeout=httpx.Timeout(None, connect=10, read=60, write=30)
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Generate summary for the table in {lang} language. Do not output any other text except for generated summaty. If you can't generate any result return just empty string.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    },
                ],
            },
        ],
        max_tokens=100,
    )

    return response.choices[0]
