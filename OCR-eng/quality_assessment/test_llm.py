import asyncio
import base64
import openai
import cv2

client = openai.AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

IMAGE = r"C:\Users\Aryan Mishra\OneDrive\Documents\Newfolder3\RESULT\MEDSAVE\02_enhanced\page_13.png"

with open(IMAGE, "rb") as f:
    image = cv2.imread(IMAGE)

    print(image.shape)
    # img = base64.b64encode(f.read()).decode()
    img = base64.b64encode(f.read()).decode()

async def main():

    r = await client.chat.completions.create(

        model="qwen2.5vl:7b",

        messages=[

            {
                "role":"user",
                "content":[

                    {
                        "type":"text",
                        "text":"Read every word."
                    },

                    {
                        "type":"image_url",
                        "image_url":{
                            "url":f"data:image/jpeg;base64,{img}"
                        }
                    }

                ]
            }

        ]

    )

    print(r.choices[0].message.content)

asyncio.run(main())