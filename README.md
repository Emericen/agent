# agent

A shell agent in one file. The model gets one tool, `bash`, and every call runs in a fresh subprocess. Nothing else.

## Setup

```
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/Emericen/agent && cd agent
```

Open `main.py` and fill in the top three lines: any OpenAI-compatible chat completions URL, a model name, and your API key.

## Run

```
uv run main.py
```

uv brings its own Python, so a blank machine needs nothing else. Ctrl-C stops a running turn, Ctrl-D quits.
