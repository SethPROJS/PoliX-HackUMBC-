PoliX

PoliX is a civic education app that helps users identify gaps in their
political knowledge and learn through diagnostics, resources,
flashcards, custom quizzes, and an AI tutor.

Requirements

Python 3.10+

Pygame

Ollama for the AI-powered chatbot and custom quiz features

Qwen 3.5 0.8B model (or another compatible Ollama model)

Setup

Install Python from https://www.python.org/

Install Pygame:

pip install pygame

Install Ollama from https://ollama.com/

Download the default PoliX model:

ollama pull qwen3.5:0.8b

Make sure Ollama is running.

Place the PoliX Python file and info.txt in the same folder.

Run the app:

python PoliX_final_annotated.py

Notes

An internet connection is useful for accessing the educational
resources linked by PoliX.

The AI features run locally through Ollama.

User information and progress are stored locally by the application.
