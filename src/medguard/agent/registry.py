import inspect
from typing import Callable, Dict, Any, List
from google.genai import types


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._declarations: List[types.FunctionDeclaration] = []

    def register(self, func: Callable):
        """
        Decorator to register a tool.
        It automatically generates the Gemini FunctionDeclaration from the docstring and type hints.
        """
        self._tools[func.__name__] = func

        params = inspect.signature(func).parameters
        properties = {}
        required = []

        for name, param in params.items():

            param_type = "string"
            if param.annotation == int:
                param_type = "integer"
            elif param.annotation == float:
                param_type = "number"
            elif param.annotation == bool:
                param_type = "boolean"

            properties[name] = {"type": param_type, "description": f"Parameter {name}"}
            if param.default == inspect.Parameter.empty:
                required.append(name)

        declaration = types.FunctionDeclaration(
            name=func.__name__,
            description=func.__doc__ or "No description provided",
            parameters=types.Schema(
                type="OBJECT", properties=properties, required=required
            ),
        )

        self._declarations.append(declaration)
        return func

    @property
    def tools_list(self) -> types.Tool:
        """Returns the Tool object formatted for Gemini"""
        return types.Tool(function_declarations=self._declarations)

    def execute(self, name: str, args: Dict[str, Any]) -> Any:
        """Executes the registered function safely"""
        if name not in self._tools:
            raise ValueError(f"Tool {name} not found")
        return self._tools[name](**args)


registry = ToolRegistry()
