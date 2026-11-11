# agent

A shell agent in one file. The model gets two tools: `bash`, where every call runs in a fresh subprocess, and `view`, which shows it a png or jpg from disk. Nothing else.

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

## History

Each run saves its conversation next to `main.py` as `history-<start time>.json`, rewritten after every message, so quitting or a crash loses nothing. A new run starts a new file. Pictures the model viewed are stored inside the file, so it can get large. These files are ignored by git.

To continue an old conversation, name its file:

```
uv run main.py history-2026-11-11-113348.json
```

The model sees that conversation exactly as it was saved, and new messages are saved to the same file.

## Long conversations

The whole conversation is sent to the model on every call. Once it passes `COMPACT_AT` tokens (100,000 unless you change it at the top of `main.py`), the model writes a summary of it and carries on from the summary, in a new history file. The old file keeps the full conversation, and the summary tells the model where that file is.
