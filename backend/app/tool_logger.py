import os
import json
import functools
import time
from typing import Dict, Any, List, Callable
import threading

# Import the tool usage tracker
from .tool_usage import add_tool_usage, update_tool_output

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Thread-local storage for tracking the current session
_session_local = threading.local()

def start_session(query_id: str) -> None:
    """Start a new logging session for a specific query"""
    _session_local.query_id = query_id
    _session_local.tool_calls = []
    
    # Clear previous log file
    log_file = os.path.join(LOGS_DIR, f"{query_id}.json")
    with open(log_file, 'w') as f:
        json.dump([], f)

def get_session_tools() -> List[Dict[str, Any]]:
    """Get the tool calls for the current session"""
    if not hasattr(_session_local, 'tool_calls'):
        return []
    return _session_local.tool_calls

def log_tool_call(tool_name: str, input_data: Dict[str, Any], output_data: Any) -> None:
    """Log a tool call to the current session"""
    if not hasattr(_session_local, 'query_id') or not hasattr(_session_local, 'tool_calls'):
        return
    
    # Record the tool call
    step = len(_session_local.tool_calls) + 1
    tool_call = {
        "step": step,
        "tool": tool_name,
        "input": input_data,
        "output": output_data,
        "timestamp": time.time()
    }
    
    # Add to in-memory list
    _session_local.tool_calls.append(tool_call)
    
    # Update the log file
    log_file = os.path.join(LOGS_DIR, f"{_session_local.query_id}.json")
    with open(log_file, 'w') as f:
        json.dump(_session_local.tool_calls, f, indent=2)
    
    # Also add to the new tool usage tracker
    add_tool_usage(tool_name, input_data, output_data)

def tool_logger(func: Callable) -> Callable:
    """Decorator to log tool usage"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Track the input but filter out config
        input_data = kwargs.copy()
        if 'config' in input_data:
            input_data.pop('config')
            
        # If positional args, convert to dict representation
        if args and len(args) > 0:
            # Get the param names from the function signature
            import inspect
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            
            # Map positional args to their parameter names
            for i, arg in enumerate(args):
                if i < len(param_names) and param_names[i] != 'config':
                    input_data[param_names[i]] = arg
        
        # Execute the tool
        try:
            result = func(*args, **kwargs)
            
            # Log the tool call
            log_tool_call(
                tool_name=func.__name__,
                input_data=input_data,
                output_data=result
            )
            
            return result
        except Exception as e:
            # Log the error
            log_tool_call(
                tool_name=func.__name__,
                input_data=input_data,
                output_data={"error": str(e)}
            )
            raise
    
    return wrapper 