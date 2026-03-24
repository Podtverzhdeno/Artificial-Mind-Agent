import os


def execute_action(action: str):

    action = action.lower()

    if action == "reflect":

        return "Agent reflected internally."

    if action == "write_journal":

        return "Agent decided to record its thoughts."

    if action == "update_memory":

        return "Agent updated its internal memory."

    if action == "create_experiment":

        os.makedirs("experiments", exist_ok=True)

        filename = f"experiments/experiment_{len(os.listdir('experiments'))+1}.txt"

        with open(filename, "w") as f:
            f.write("Experiment placeholder")

        return f"Created {filename}"

    return "Unknown action"