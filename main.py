import base64
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

URL = ""
MODEL = ""
API_KEY = ""  # that's right. be careful.

# Past this many tokens, the conversation is replaced by a summary of itself.
COMPACT_AT = 100_000

SUMMARIZE = (
    "Stop here and write a summary of this whole conversation. The summary will "
    "replace the conversation and you will continue from it alone, so include "
    "what the user wants, their latest request word for word, what you did and "
    "found (exact paths, commands and values that matter), and what is left to do."
)


class Agent:
    def __init__(self):
        self.history = new_history()
        self.tokens = 0  # size of the conversation, as the model last counted it
        self.messages = [
            {
                "role": "system",
                "content": "You are a helpful agent with access to a shell. Each command runs in a fresh subprocess. You can also view a png or jpg file. Respond in plain text only, no markdown. Only use bullet points if absolutely necessary, otherwise regular paragraphs is good enough. Respond concisely!",
            }
        ]

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": "Run a shell command on this machine.",
                    "parameters": {
                        "type": "object",
                        "properties": {"command": {"type": "string"}},
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "view",
                    "description": "Look at a png or jpg file on this machine.",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
            },
        ]

    def resume(self, history):
        # Continue the conversation saved in an old file, and keep saving to it.
        self.history = Path(history)
        self.messages = json.loads(self.history.read_text(encoding="utf-8"))

    def turn(self, text):
        self._add({"role": "user", "content": text})
        while True:
            response = self._send_request(self.messages)
            self._add(response)
            if response.get("content"):
                print(response["content"])
                print()
            if not response.get("tool_calls"):
                self._compact()
                return
            images = []
            for call in response["tool_calls"]:
                arguments = json.loads(call["function"]["arguments"])
                if call["function"]["name"] == "view":
                    output, image = self._view(arguments["path"])
                    images.append(image)
                    print_tool_call(f"view {arguments['path']}", output)
                else:
                    output = self._execute(arguments["command"])
                    print_tool_call(f"$ {arguments['command']}", output)
                self._add(
                    {"role": "tool", "tool_call_id": call["id"], "content": output}
                )
            # Chat completions only take images in user messages, so the viewed
            # files follow the tool results as one user message.
            images = [image for image in images if image]
            if images:
                self._add({"role": "user", "content": images})
            self._compact()

    def interrupt(self):
        if self.messages[-1].get("tool_calls"):
            self.messages.pop()
            self._save()

    def _add(self, message):
        self.messages.append(message)
        self._save()

    def _save(self):
        # Write a whole new file, then swap it in, so stopping mid-write
        # never leaves half a file.
        draft = self.history.with_suffix(".tmp")
        text = json.dumps(self.messages, indent=2, ensure_ascii=False)
        draft.write_text(text, encoding="utf-8")
        draft.replace(self.history)

    def _compact(self):
        # Once the conversation is past COMPACT_AT tokens, the model summarizes
        # it and carries on from the summary. The full conversation stays in
        # its history file, and the summary starts a new one.
        if self.tokens < COMPACT_AT:
            return
        ask = {"role": "user", "content": SUMMARIZE}
        summary = self._send_request(self.messages + [ask]).get("content")
        if not summary:
            return
        old = self.history
        self.history = new_history()
        note = (
            "This conversation got long, so its earlier part was replaced by the "
            f"summary below. The full record is the JSON file {old}. Search it if "
            "you need an exact detail, do not read it whole."
        )
        summary = {"role": "user", "content": f"{note}\n\n{summary}"}
        self.messages = [self.messages[0], summary]
        self._save()
        print(f"\033[2mcompacted {old.name} into {self.history.name}\033[0m")  # dim
        print()

    def _send_request(self, messages):
        body = {"model": MODEL, "messages": messages, "tools": self.tools}
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
        request = urllib.request.Request(
            URL, data=json.dumps(body).encode(), headers=headers
        )
        with urllib.request.urlopen(request) as response:
            reply = json.load(response)
        self.tokens = reply["usage"]["total_tokens"]
        return reply["choices"][0]["message"]

    def _execute(self, command):
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return "[timed out after 120s]"
        return result.stdout + result.stderr + f"[exit {result.returncode}]"

    def _view(self, path):
        try:
            with open(path, "rb") as file:
                data = base64.b64encode(file.read()).decode()
        except OSError as error:
            return str(error), None
        kind = "png" if path.lower().endswith(".png") else "jpeg"
        url = f"data:image/{kind};base64,{data}"
        return "[image attached below]", {
            "type": "image_url",
            "image_url": {"url": url},
        }


def new_history():
    # A new file next to this script, named by the time. Never an existing one.
    while True:
        name = time.strftime("history-%Y-%m-%d-%H%M%S.json")
        path = Path(__file__).with_name(name)
        if not path.exists():
            return path
        time.sleep(1)


def print_tool_call(label, output):
    lines = output.splitlines()
    if len(lines) > 8:
        hidden = len(lines) - 8
        lines = lines[:8] + [f"... {hidden} more lines"]
    print(f"\033[2m{label}")  # dim
    print("\n".join(lines) + "\033[0m")  # reset
    print()


def main():
    agent = Agent()
    if len(sys.argv) > 1:
        agent.resume(sys.argv[1])
        count = len(agent.messages)
        print(f"\033[2mcontinuing {sys.argv[1]}, {count} messages\033[0m")  # dim
    print()
    while True:
        try:
            text = input("\033[33m> \033[0m\033[3m")  # italic, yellow arrow, white text
        except (EOFError, KeyboardInterrupt):
            print("\033[0m")  # reset
            break
        print("\033[0m")  # reset
        try:
            agent.turn(text)
        except KeyboardInterrupt:
            print("\n(interrupted)\n")
            agent.interrupt()


if __name__ == "__main__":
    main()
