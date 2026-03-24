from core.brain import ask_llm


def plan_action(thought):

    prompt = f"""
You are an autonomous AI agent.

Your thought:
{thought}

Choose ONE action to perform.

Available actions:

1. reflect
2. write_journal
3. update_memory
4. create_experiment

Return only the action name.
"""

    action = ask_llm(prompt)

    return action.strip()