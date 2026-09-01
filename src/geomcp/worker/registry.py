from __future__ import annotations
import os, socket, time
from dataclasses import dataclass
from typing import Any, Callable
from geomcp.exceptions import WorkerError

TaskHandler = Callable[[dict[str, Any], dict[str, Any]], Any]
TaskValidator = Callable[[dict[str, Any], dict[str, Any]], None]

@dataclass(frozen=True, slots=True)
class TaskDefinition:
    name: str
    executor: str
    handler: TaskHandler
    timeout: float = 300.0
    validator: TaskValidator | None = None
    def validate(self, input_data: dict[str, Any], parameters: dict[str, Any]) -> None:
        if not isinstance(input_data, dict) or not isinstance(parameters, dict):
            raise WorkerError("Job input and parameters must be mappings")
        if self.validator is not None: self.validator(input_data, parameters)

class TaskRegistry:
    def __init__(self): self._tasks: dict[str, TaskDefinition] = {}
    def register(self, task: TaskDefinition):
        if task.name in self._tasks: raise ValueError(f"Duplicate task: {task.name}")
        self._tasks[task.name] = task
    def get(self, name: str) -> TaskDefinition:
        try: return self._tasks[name]
        except KeyError as exc: raise WorkerError(f"Unregistered task type: {name}") from exc

def _no_args(input_data, parameters):
    if input_data or parameters: raise WorkerError("This task accepts no input or parameters")
def _delay_args(input_data, parameters):
    if input_data: raise WorkerError("cpu.delay accepts no input")
    unknown=set(parameters)-{"seconds"}
    if unknown: raise WorkerError(f"Unknown cpu.delay parameters: {', '.join(sorted(unknown))}")
    seconds=float(parameters.get("seconds",0.0))
    if seconds < 0 or seconds > 30: raise WorkerError("seconds must be between 0 and 30")
def _healthcheck(input_data, parameters):
    return {"hostname": socket.gethostname(), "pid": os.getpid(), "cuda_visible_devices": os.getenv("CUDA_VISIBLE_DEVICES"), "ok": True}
def _delay(input_data, parameters):
    seconds=float(parameters.get("seconds",0.0)); time.sleep(seconds); return {"slept":seconds}

def build_task_registry() -> TaskRegistry:
    r=TaskRegistry()
    r.register(TaskDefinition("cpu.healthcheck","cpu",_healthcheck,30.0,_no_args))
    r.register(TaskDefinition("cpu.delay","cpu",_delay,1.0,_delay_args))
    r.register(TaskDefinition("gpu.healthcheck","gpu",_healthcheck,30.0,_no_args))
    return r
