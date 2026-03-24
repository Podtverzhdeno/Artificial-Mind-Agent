from agents.thinker import think
from agents.planner import plan_action
from agents.critic import critique

from core.memory import Memory
from core.executor import execute_action


def run():

    memory = Memory()

    cycle = 1

    while True:

        print(f"\n===== CYCLE {cycle} =====")

        goal = memory.get_goal()
        recent_memory = memory.get_recent()

        # 1. THINK
        thought = think(goal, recent_memory)

        print("\nThought:")
        print(thought)

        # 2. PLAN
        action = plan_action(thought)

        print("\nAction:")
        print(action)

        # 3. EXECUTE
        result = execute_action(action)

        print("\nResult:")
        print(result)

        # 4. CRITIQUE
        analysis = critique(goal, action, result)

        print("\nCritique:")
        print(analysis)

        # 5. SAVE
        memory.store_cycle(
            cycle=cycle,
            thought=thought,
            action=action,
            result=result,
            critique=analysis
        )

        cycle += 1


if __name__ == "__main__":
    run()