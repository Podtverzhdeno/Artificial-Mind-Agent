import os


class Memory:

    def __init__(self):

        self.goal_path = "config/goal.md"
        self.journal_path = "memory/journal"

        os.makedirs(self.journal_path, exist_ok=True)

    def get_goal(self):

        with open(self.goal_path, "r", encoding="utf-8") as f:
            return f.read()

    def get_recent(self, n=3):

        files = sorted(os.listdir(self.journal_path))[-n:]

        history = []

        for file in files:
            path = os.path.join(self.journal_path, file)

            with open(path, "r", encoding="utf-8") as f:
                history.append(f.read())

        return "\n\n".join(history)

    def store_cycle(self, cycle, thought, action, result, critique):

        filename = f"{cycle:04d}.md"

        path = os.path.join(self.journal_path, filename)

        content = f"""
# Cycle {cycle}

## Thought
{thought}

## Action
{action}

## Result
{result}

## Critique
{critique}
"""

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)