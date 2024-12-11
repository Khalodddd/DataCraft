from transformers import pipeline

# Load the GPT-2 model from Hugging Face
generator = pipeline('text-generation', model='gpt2')

# Function to ask Hugging Face GPT-2 and get the response
def ask_huggingface(prompt):
    response = generator(prompt, max_length=100, num_return_sequences=1)
    return response[0]['generated_text']
