from typing import Type, Dict, Any, Union, get_origin, get_args, List
from pydantic import BaseModel
from datetime import datetime, date

# Mapping of Python types to SQL types
TYPE_MAPPING: Dict[Type, str] = {
    str: "TEXT",
    int: "INTEGER",
    float: "DOUBLE",
    bool: "BOOLEAN",
    dict: "JSON",
    list: "JSON",
    datetime: "TIMESTAMPTZ",
    date: "DATE",
}

def resolve_type(field_type):
    """Resolve real type from Optional / Union / Annotated wrappers."""
    origin = get_origin(field_type)
    if origin is Union:
        args = get_args(field_type)
        non_none = [arg for arg in args if arg is not type(None)]
        return non_none[0] if non_none else str
    return field_type

def is_field_nullable(field) -> bool:
    """Determine if a field is nullable (optional)."""
    return field.default is None or get_origin(field.annotation) is Union

def generate_create_statement(model: Type[BaseModel], table_name: str, primary_keys: List[str]) -> str:
    """
    Generate a CREATE TABLE SQL statement from a Pydantic model.
    """
    columns = []
    for name, field in model.model_fields.items():
        real_type = resolve_type(field.annotation)
        sql_type = TYPE_MAPPING.get(real_type, "TEXT")  # fallback to TEXT
        not_null = "NOT NULL" if not is_field_nullable(field) else ""
        columns.append(f"{name} {sql_type} {not_null}".strip())

    columns_sql = ",\n    ".join(columns)

    create_statement = f"CREATE TABLE IF NOT EXISTS {table_name} "
    if isinstance(primary_keys, list):
        create_statement += f"({columns_sql}, PRIMARY KEY ({','.join(primary_keys)}))"
    elif primary_keys:
        create_statement += f"({columns_sql}, PRIMARY KEY {primary_keys})"
    else:
        create_statement += f"({columns_sql})"

    return create_statement.strip()
