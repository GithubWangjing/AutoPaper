try:
    from openai import OpenAI
    print('OpenAI import successful!')
except Exception as e:
    print(f'Error: {e}')
