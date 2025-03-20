from openai import OpenAI
import os

# Initialize the OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "")
)

# Test a simple completion
try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ],
        temperature=0.7,
        max_tokens=100
    )
    print("OpenAI API call successful!")
    print(f"Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"Error: {str(e)}")

print("Test complete!") 