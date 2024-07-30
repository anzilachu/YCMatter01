import os
import re
from groq import Groq

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

def analyze_startup(idea):
    prompt = f"""Analyze the market potential of this startup idea: {idea}. 
    Provide a score from 1-10 for each of these categories: Innovation, Market Size, Competition, Scalability, and Profitability. Also provide a brief explanation for each score."""
    
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama3-8b-8192",
    )
    return chat_completion.choices[0].message.content

def parse_scores(analysis):
    categories = ['Innovation', 'Market Size', 'Competition', 'Scalability', 'Profitability']
    scores = {}
    for category in categories:
        match = re.search(f"{category}:\s*(\d+)", analysis)
        if match:
            scores[category] = int(match.group(1))
    return scores

def format_analysis_text(analysis):
    # Convert **text** to <h2>text</h2>
    analysis = re.sub(r'\*\*(.*?)\*\*', r'<h2>\1</h2>', analysis)
    # Convert *text* to <h3>text</h3>
    analysis = re.sub(r'\*(.*?)\*', r'<h3>\1</h3>', analysis)
    return analysis