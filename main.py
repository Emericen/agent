import json
import subprocess
import urllib.request

URL = ""
MODEL = ""
API_KEY = ""  # that's right. be careful.


class Agent:
    def __init__(self):
        self.messages = [
            {
                "role": "system",
                "content": "You are a helpful agent with access to a shell. Each command runs in a fresh subprocess. Respond in plain text only, no markdown. Only use bullet points if absolutely necessary, otherwise regular paragraphs is good enough. Respond concisely!",
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
            }
        ]

    def turn(self, text):
        self.messages.append({"role": "user", "content": text})
        while True:
            response = self._send_request()
            self.messages.append(response)
            if response.get("content"):
                print(response["content"])
                print()
            if not response.get("tool_calls"):
                return
            for call in response["tool_calls"]:
                command = json.loads(call["function"]["arguments"])["command"]
                output = self._execute(command)
                print_tool_call(command, output)
                self.messages.append(
                    {"role": "tool", "tool_call_id": call["id"], "content": output}
                )

    def interrupt(self):
        if self.messages[-1].get("tool_calls"):
            self.messages.pop()

    def _send_request(self):
        body = {"model": MODEL, "messages": self.messages, "tools": self.tools}
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
        request = urllib.request.Request(
            URL, data=json.dumps(body).encode(), headers=headers
        )
        with urllib.request.urlopen(request) as response:
            return json.load(response)["choices"][0]["message"]

    def _execute(self, command):
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=120
            )
        except subprocess.TimeoutExpired:
            return "[timed out after 120s]"
        return result.stdout + result.stderr + f"[exit {result.returncode}]"


def print_tool_call(command, output):
    lines = output.splitlines()
    if len(lines) > 8:
        hidden = len(lines) - 8
        lines = lines[:8] + [f"... {hidden} more lines"]
    print(f"\033[2m$ {command}")  # dim
    print("\n".join(lines) + "\033[0m")  # reset
    print()


def main():
    agent = Agent()
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
