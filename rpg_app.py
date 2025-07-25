# rpg_app.py

import os
import json
import gradio as gr
from fastapi import FastAPI
from together import Together
from helper import get_together_api_key#, load_world, save_world

def save_world(world, filename):
    with open(filename, 'w') as f:
        json.dump(world, f)

def load_world(filename):
    with open(filename, 'r') as f:
        return json.load(f)
# Initialize Together API client
client = Together(api_key=get_together_api_key())

# ----- WORLD GENERATION (L1) -----
system_prompt = """
You are a fantasy world builder. Your job is to create immersive and creative environments that players would love.
Use simple, clear language, 3–5 sentences max. Return only plain text.
"""

def generate_world():
    world_prompt = """
Generate a creative fantasy world with cities built on massive beasts.

Format:
World Name: <name>
World Description: <description>

World Name:"""

    response = client.chat.completions.create(
        model="meta-llama/Llama-3-70b-chat-hf",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": world_prompt}
        ]
    )
    text = response.choices[0].message.content.strip()
    name = text.split('\n')[0].replace("World Name:", "").strip()
    desc = '\n'.join(text.split('\n')[1:]).replace("World Description:", "").strip()
    return {"name": name, "description": desc}


def generate_kingdoms(world):
    prompt = f"""
Create 3 kingdoms in the fantasy world below.

World Name: {world['name']}
World Description: {world['description']}

Format:
Kingdom 1 Name: ...
Kingdom 1 Description: ...
...
Kingdom 3 Description:"""

    response = client.chat.completions.create(
        model="meta-llama/Llama-3-70b-chat-hf",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    kingdoms = {}
    raw = response.choices[0].message.content
    for entry in raw.strip().split('\n\n'):
        lines = entry.strip().split('\n')
        name = lines[0].split(": ")[1].strip()
        desc = lines[1].split(": ")[1].strip()
        kingdoms[name] = {"name": name, "description": desc, "world": world['name']}
    return kingdoms


def generate_towns(world, kingdom):
    prompt = f"""
Create 3 towns for the kingdom in this world.

World: {world['name']} — {world['description']}
Kingdom: {kingdom['name']} — {kingdom['description']}

Format:
Town 1 Name: ...
Town 1 Description: ...
...
Town 3 Description:"""

    response = client.chat.completions.create(
        model="meta-llama/Llama-3-70b-chat-hf",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    towns = {}
    raw = response.choices[0].message.content
    for entry in raw.strip().split('\n\n'):
        lines = entry.strip().split('\n')
        name = lines[0].split(": ")[1].strip()
        desc = lines[1].split(": ")[1].strip()
        towns[name] = {"name": name, "description": desc}
    return towns


def generate_npcs(world, kingdom, town):
    prompt = f"""
Create 3 characters based on the following:

World: {world['name']} — {world['description']}
Kingdom: {kingdom['name']} — {kingdom['description']}
Town: {town['name']} — {town['description']}

Format:
Character 1 Name: ...
Character 1 Description: ...
...
Character 3 Description:"""

    response = client.chat.completions.create(
        model="meta-llama/Llama-3-70b-chat-hf",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    npcs = {}
    raw = response.choices[0].message.content
    for entry in raw.strip().split('\n\n'):
        lines = entry.strip().split('\n')
        name = lines[0].split(": ")[1].strip()
        desc = lines[1].split(": ")[1].strip()
        npcs[name] = {"name": name, "description": desc}
    return npcs

def create_game_world():
    world = generate_world()
    kingdoms = generate_kingdoms(world)
    for k in kingdoms.values():
        towns = generate_towns(world, k)
        for t in towns.values():
            npcs = generate_npcs(world, k, t)
            t["npcs"] = npcs
        k["towns"] = towns
    world["kingdoms"] = kingdoms
    save_world(world, 'shared_data/YourWorld_L1.json')
    return world

# ----- RPG LOOP (L2) -----

def generate_intro(world, kingdom, town, character):
    prompt = f"""
You are an AI Game Master.

Write a 2–4 sentence story intro.
- Write in second person.
- Present tense.
- Start with the character and their background.
- Then describe the environment around them.

World: {world}
Kingdom: {kingdom}
Town: {town}
Character: {character}
"""
    response = client.chat.completions.create(
        model="meta-llama/Llama-3-70b-chat-hf",
        temperature=1.0,
        messages=[
            {"role": "system", "content": "You are an AI Game Master."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()


def run_action(message, history, game_state):
    if message.lower().strip() == "start game":
        return game_state["start"]

    prompt = f"""
You are an AI Game Master. Write 1–3 sentences in second person and present tense.

World: {game_state['world']}
Kingdom: {game_state['kingdom']}
Town: {game_state['town']}
Character: {game_state['character']}
"""

    messages = [{"role": "system", "content": prompt}]
    for action in history:
        messages.append({"role": "assistant", "content": action[0]})
        messages.append({"role": "user", "content": action[1]})
    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model="meta-llama/Llama-3-70b-chat-hf",
        messages=messages
    )
    return response.choices[0].message.content.strip()

# Load or generate world
try:
    world = load_world('shared_data/YourWorld_L1.json')
except:
    world = create_game_world()

# Pick one kingdom, town, character for now
kingdom = list(world["kingdoms"].values())[0]
town = list(kingdom["towns"].values())[0]
character = list(town["npcs"].values())[0]
intro = generate_intro(world["description"], kingdom["description"], town["description"], character["description"])

# Create game state
game_state = {
    "world": world["description"],
    "kingdom": kingdom["description"],
    "town": town["description"],
    "character": character["description"],
    "start": intro
}

def main_loop(message, history):
    return run_action(message, history, game_state)

# Launch Gradio App
demo = gr.ChatInterface(
    fn=main_loop,
    chatbot=gr.Chatbot(height=300, placeholder="Say something to begin..."),
    textbox=gr.Textbox(placeholder="Type your action here...", container=False),
    title="🧙‍♂️ AI RPG World Generator",
    theme="soft",
    examples=["start game", "Look around", "Talk to someone"],
    retry_btn="Retry",
    undo_btn="Undo",
    clear_btn="Reset"
)

app = FastAPI()
app = gr.mount_gradio_app(app, demo, path="/")
