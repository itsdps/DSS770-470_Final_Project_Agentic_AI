from typing import Type, Dict, Any
from pydantic import BaseModel


def pydantic_to_openai_schema(model_cls: Type[BaseModel], name: str) -> Dict[str, Any]:
    """
    Convert a Pydantic model to an OpenAI-compatible strict JSON schema.
    
    Recursively enforces additionalProperties: false on all objects to comply
    with OpenAI's strict JSON schema mode.
    
    Args:
        model_cls: A Pydantic BaseModel class to convert.
        name: The name for the schema (used by OpenAI API).
    
    Returns:
        A dict with keys 'name', 'strict', and 'schema' ready for OpenAI's
        response_format parameter.
    
    Raises:
        AttributeError: If model_cls is not a Pydantic model.
        ValueError: If name is empty.
    """
    if not name or not isinstance(name, str):
        raise ValueError("name must be a non-empty string")
    
    if not hasattr(model_cls, 'model_json_schema'):
        raise AttributeError(f"{model_cls} is not a Pydantic model")
    
    schema = model_cls.model_json_schema()

    def enforce_no_extra(node: Any) -> None:
        if not isinstance(node, dict):
            return
        if node.get("type") == "object":
            node.setdefault("additionalProperties", False)
            for prop in node.get("properties", {}).values():
                enforce_no_extra(prop)
        if node.get("type") == "array" and "items" in node:
            enforce_no_extra(node["items"])
        # Recursively process $defs/definitions
        if "$defs" in node:
            for def_schema in node["$defs"].values():
                enforce_no_extra(def_schema)
        if "definitions" in node:
            for def_schema in node["definitions"].values():
                enforce_no_extra(def_schema)

    enforce_no_extra(schema)
    return {"name": name, "strict": True, "schema": schema}
