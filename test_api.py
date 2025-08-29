from openai import OpenAI
import os

client = OpenAI()

resp = client.embeddings.create(
    model="text-embedding-3-small",
    input=["Hello, world!"]
)

print("✅ Embedding działa, długość wektora:", len(resp.data[0].embedding))
