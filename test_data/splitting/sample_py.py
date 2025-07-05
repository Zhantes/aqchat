import datetime
import random
from typing import List

def generate_task_id() -> str:
    """Utility function to generate a random task ID."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    random_part = random.randint(1000, 9999)
    return f"TASK-{timestamp}-{random_part}"

def is_valid_description(desc: str) -> bool:
    """Utility function to validate a task description."""
    return len(desc.strip()) > 0

class Task:
    """
    Represents a single task in a task manager.
    """

    def __init__(self, description: str):
        if not is_valid_description(description):
            raise ValueError("Description must not be empty")

        self._id = generate_task_id()
        self._description = description
        self._created_at = datetime.datetime.now()
        self._completed = False

    @property
    def id(self) -> str:
        return self._id

    @property
    def description(self) -> str:
        return self._description

    @property
    def created_at(self) -> datetime.datetime:
        return self._created_at

    @property
    def is_completed(self) -> bool:
        return self._completed

    def mark_completed(self):
        self._completed = True

    def __str__(self) -> str:
        status = "X" if self._completed else " "
        return f"[{status}] {self._description} (Created: {self._created_at.strftime('%Y-%m-%d %H:%M:%S')})"

class TaskManager:
    """
    Manages a collection of tasks.
    """

    def __init__(self):
        self._tasks: List[Task] = []

    def add_task(self, description: str) -> Task:
        task = Task(description)
        self._tasks.append(task)
        return task

    def list_tasks(self) -> List[Task]:
        return self._tasks

    def get_incomplete_tasks(self) -> List[Task]:
        return [task for task in self._tasks if not task.is_completed]

    def complete_task(self, task_id: str) -> bool:
        for task in self._tasks:
            if task.id == task_id:
                task.mark_completed()
                return True
        return False

# Run if script is executed directly
if __name__ == "__main__":
    manager = TaskManager()

    print("Adding tasks...")
    manager.add_task("Buy groceries")
    manager.add_task("Walk the dog")
    manager.add_task("Read a book")

    print("\nCurrent tasks:")
    for task in manager.list_tasks():
        print(task)

    print("\nCompleting the first task...")
    first_task_id = manager.list_tasks()[0].id
    manager.complete_task(first_task_id)

    print("\nIncomplete tasks:")
    for task in manager.get_incomplete_tasks():
        print(task)
