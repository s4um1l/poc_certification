"""
Tool usage tracking for agent operations
"""
import json
from typing import Dict, Any, List
import uuid
import threading

# Thread-local storage for tracking tool usage
_local = threading.local()

def reset_tracker():
    """Reset the tool usage tracker for a new session"""
    _local.tool_calls = []
    _local.tool_ids = {}  # Map tool call IDs to our internal IDs

def add_tool_usage(tool_name: str, tool_input: Dict[str, Any], tool_output: Any = None, tool_id: str = None):
    """Add a tool usage record to the tracker"""
    if not hasattr(_local, 'tool_calls'):
        reset_tracker()
        
    # Generate a unique ID for this tool call
    internal_id = str(uuid.uuid4())
    
    # Create the tool usage record
    step = len(_local.tool_calls) + 1
    tool_call = {
        "id": internal_id,
        "step": step,
        "tool": tool_name,
        "input": tool_input,
        "output": tool_output
    }
    
    # Add to in-memory list
    _local.tool_calls.append(tool_call)
    
    # If there's an external tool ID, map it to our internal ID
    if tool_id:
        _local.tool_ids[tool_id] = internal_id
        
    return internal_id

def update_tool_output(tool_id: str, output: Any):
    """Update the output of a specific tool call"""
    if not hasattr(_local, 'tool_calls'):
        return False
        
    # Check if this is an external ID that needs mapping
    internal_id = _local.tool_ids.get(tool_id, tool_id)
    
    # Find and update the matching tool call
    for tool_call in _local.tool_calls:
        if tool_call.get("id") == internal_id:
            tool_call["output"] = output
            return True
            
    return False

def get_tool_usage() -> List[Dict[str, Any]]:
    """Get all tool usage records for the current session"""
    if not hasattr(_local, 'tool_calls'):
        return []
        
    return _local.tool_calls 