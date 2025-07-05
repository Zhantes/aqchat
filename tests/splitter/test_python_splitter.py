from pathlib import Path
from typing import List
from pipelines.boundary_splitter import CodeBoundaryTextSplitter
from pipelines.detectors import CodeBoundaryDetector, PythonBoundaryDetector

def _get_test_code_and_detector() -> str | None:
    code = Path(f"test_data/splitting/sample_py.py").read_text("utf-8")
    detector = PythonBoundaryDetector()
    
    return code, detector

def _split_with_detector(code: str, detector: CodeBoundaryDetector) -> List[str]:
    splitter = CodeBoundaryTextSplitter()
    chunks = [chunk.strip() for chunk in splitter.split_text(code, boundary_detector=detector)]
    return chunks

def test_python_imports():
    """This tests if the splitter can successfully split imports
    at the top of the code file.
    """
    code, detector = _get_test_code_and_detector()
    result = _split_with_detector(code, detector)

    expected = """import datetime
import random
from typing import List"""
    
    assert expected in result

def test_python_func_isolated():
    """This tests if the splitter can successfully split a function
    which is not within a class.
    """
    code, detector = _get_test_code_and_detector()
    result = _split_with_detector(code, detector)

    expected = """def is_valid_description(desc: str) -> bool:
    \"\"\"Utility function to validate a task description.\"\"\"
    return len(desc.strip()) > 0"""
    
    assert expected in result

def test_python_class():
    """This tests if the splitter can successfully split an entire
    class definition.
    """
    code, detector = _get_test_code_and_detector()
    result = _split_with_detector(code, detector)

    expected = """class TaskManager:
    \"\"\"
    Manages a collection of tasks.
    \"\"\"

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
        return False"""
    
    assert expected in result

def test_python_func_class_member():
    """This tests if the splitter can successfully split a function
    that sits inside a class definition.
    """
    code, detector = _get_test_code_and_detector()
    result = _split_with_detector(code, detector)

    expected = """def complete_task(self, task_id: str) -> bool:
        for task in self._tasks:
            if task.id == task_id:
                task.mark_completed()
                return True
        return False"""
    
    assert expected in result

def test_python_main_code():
    """This tests if the splitter can successfully split code at the end
    of the file which is not within a function or class definition.
    """
    code, detector = _get_test_code_and_detector()
    result = _split_with_detector(code, detector)

    expected = """# Run if script is executed directly
if __name__ == "__main__":
    manager = TaskManager()

    print("Adding tasks...")
    manager.add_task("Buy groceries")
    manager.add_task("Walk the dog")
    manager.add_task("Read a book")

    print("\\nCurrent tasks:")
    for task in manager.list_tasks():
        print(task)

    print("\\nCompleting the first task...")
    first_task_id = manager.list_tasks()[0].id
    manager.complete_task(first_task_id)

    print("\\nIncomplete tasks:")
    for task in manager.get_incomplete_tasks():
        print(task)"""
    
    assert expected in result