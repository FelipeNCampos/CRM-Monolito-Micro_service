import json
from collections import OrderedDict
from typing import Any

from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse


def build_swagger_ui_with_postman_button(
    *,
    openapi_url: str,
    title: str,
    postman_collection_url: str,
) -> HTMLResponse:
    response = get_swagger_ui_html(openapi_url=openapi_url, title=title)
    html = response.body.decode("utf-8")
    injection = f"""
<style>
  .postman-download-link {{
    position: fixed;
    top: 1rem;
    right: 1rem;
    z-index: 9999;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.75rem 1rem;
    border-radius: 999px;
    background: #ff6c37;
    color: #fff;
    font-family: Arial, sans-serif;
    font-size: 0.95rem;
    font-weight: 700;
    text-decoration: none;
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.2);
  }}

  .postman-download-link:hover {{
    background: #e85d2a;
  }}

  @media (max-width: 720px) {{
    .postman-download-link {{
      top: auto;
      right: 1rem;
      bottom: 1rem;
      left: 1rem;
    }}
  }}
</style>
<script>
  window.addEventListener("load", function () {{
    if (document.getElementById("postman-download-link")) {{
      return;
    }}

    var link = document.createElement("a");
    link.id = "postman-download-link";
    link.className = "postman-download-link";
    link.href = {json.dumps(postman_collection_url)};
    link.download = "crm-backend-postman-collection.json";
    link.textContent = "Baixar collection Postman";
    document.body.appendChild(link);
  }});
</script>
"""
    return HTMLResponse(
        content=html.replace("</body>", f"{injection}</body>"),
        status_code=response.status_code,
        headers=_safe_html_headers(response.headers),
    )


def build_redoc_page(*, openapi_url: str, title: str) -> HTMLResponse:
    response = get_redoc_html(openapi_url=openapi_url, title=title)
    return HTMLResponse(
        content=response.body.decode("utf-8"),
        status_code=response.status_code,
        headers=_safe_html_headers(response.headers),
    )


def _safe_html_headers(headers: Any) -> dict[str, str]:
    copied_headers = dict(headers)
    copied_headers.pop("content-length", None)
    copied_headers.pop("Content-Length", None)
    copied_headers.pop("content-type", None)
    copied_headers.pop("Content-Type", None)
    return copied_headers


def build_postman_collection(*, openapi_schema: dict[str, Any], base_url: str) -> dict[str, Any]:
    folders: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()

    for path, path_item in openapi_schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.lower() not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "options",
                "head",
            }:
                continue

            tag = (operation.get("tags") or ["Geral"])[0]
            folders.setdefault(tag, []).append(
                _build_postman_item(
                    path=path,
                    method=method.upper(),
                    operation=operation,
                    components=openapi_schema.get("components", {}),
                )
            )

    return {
        "info": {
            "name": f"{openapi_schema.get('info', {}).get('title', 'API')} - Postman Collection",
            "description": openapi_schema.get("info", {}).get("description", ""),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "version": openapi_schema.get("info", {}).get("version", "1.0.0"),
        },
        "variable": [
            {"key": "baseUrl", "value": base_url.rstrip("/")},
            {"key": "bearerToken", "value": ""},
        ],
        "item": [
            {
                "name": folder_name,
                "item": items,
            }
            for folder_name, items in folders.items()
        ],
    }


def _build_postman_item(
    *,
    path: str,
    method: str,
    operation: dict[str, Any],
    components: dict[str, Any],
) -> dict[str, Any]:
    raw_path = path
    path_variables = []
    query_params = []
    headers = []

    for parameter in _collect_parameters(operation, components):
        location = parameter.get("in")
        name = parameter.get("name", "param")
        description = parameter.get("description", "")
        example = _parameter_example(parameter, components)

        if location == "path":
            raw_path = raw_path.replace(f"{{{name}}}", f":{name}")
            path_variables.append(
                {
                    "key": name,
                    "value": str(example),
                    "description": description,
                }
            )
        elif location == "query":
            query_params.append(
                {
                    "key": name,
                    "value": str(example),
                    "description": description,
                }
            )
        elif location == "header":
            headers.append(
                {
                    "key": name,
                    "value": str(example),
                    "description": description,
                }
            )

    body, content_type_header = _build_request_body(operation, components)
    if content_type_header:
        headers.append(content_type_header)

    request_data: dict[str, Any] = {
        "method": method,
        "header": headers,
        "url": {
            "raw": f"{{{{baseUrl}}}}{raw_path}",
            "host": ["{{baseUrl}}"],
            "path": [segment for segment in raw_path.strip("/").split("/") if segment],
        },
    }

    if path_variables:
        request_data["url"]["variable"] = path_variables
    if query_params:
        request_data["url"]["query"] = query_params
    if body:
        request_data["body"] = body
    if _operation_requires_bearer_auth(operation):
        request_data["auth"] = {
            "type": "bearer",
            "bearer": [
                {
                    "key": "token",
                    "value": "{{bearerToken}}",
                    "type": "string",
                }
            ],
        }

    description = operation.get("description") or operation.get("summary") or ""
    return {
        "name": operation.get("summary") or f"{method} {path}",
        "request": request_data,
        "response": [],
        "description": description,
    }


def _collect_parameters(operation: dict[str, Any], components: dict[str, Any]) -> list[dict[str, Any]]:
    parameters = []
    for parameter in operation.get("parameters", []):
        parameters.append(_resolve_schema(parameter, components))
    return parameters


def _build_request_body(
    operation: dict[str, Any], components: dict[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    request_body = operation.get("requestBody")
    if not request_body:
        return None, None

    request_body = _resolve_schema(request_body, components)
    content = request_body.get("content", {})
    if not content:
        return None, None

    content_type = _pick_content_type(content)
    media_type = content[content_type]
    schema = _resolve_schema(media_type.get("schema", {}), components)
    example = media_type.get("example")
    if example is None:
        example = _schema_example(schema, components)

    if content_type == "application/json":
        return (
            {
                "mode": "raw",
                "raw": json.dumps(example, indent=2, ensure_ascii=False),
                "options": {"raw": {"language": "json"}},
            },
            {"key": "Content-Type", "value": content_type},
        )

    if content_type in {"application/x-www-form-urlencoded", "multipart/form-data"}:
        fields = []
        if isinstance(example, dict):
            for key, value in example.items():
                fields.append({"key": key, "value": str(value), "type": "text"})

        return (
            {
                "mode": "formdata" if content_type == "multipart/form-data" else "urlencoded",
                "formdata" if content_type == "multipart/form-data" else "urlencoded": fields,
            },
            {"key": "Content-Type", "value": content_type},
        )

    return (
        {
            "mode": "raw",
            "raw": str(example or ""),
        },
        {"key": "Content-Type", "value": content_type},
    )


def _pick_content_type(content: dict[str, Any]) -> str:
    for preferred in (
        "application/json",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
        "text/plain",
    ):
        if preferred in content:
            return preferred
    return next(iter(content))


def _resolve_schema(schema: dict[str, Any], components: dict[str, Any]) -> dict[str, Any]:
    if "$ref" not in schema:
        return schema

    ref = schema["$ref"]
    if not ref.startswith("#/components/"):
        return schema

    resolved: Any = components
    for part in ref.removeprefix("#/components/").split("/"):
        resolved = resolved[part]
    if isinstance(resolved, dict) and "$ref" in resolved:
        return _resolve_schema(resolved, components)
    return resolved


def _schema_example(
    schema: dict[str, Any], components: dict[str, Any], seen: set[str] | None = None
) -> Any:
    if seen is None:
        seen = set()

    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in seen:
            return {}
        seen.add(ref)
        return _schema_example(_resolve_schema(schema, components), components, seen)

    if "example" in schema:
        return schema["example"]

    if schema.get("enum"):
        return schema["enum"][0]

    if "allOf" in schema:
        merged: dict[str, Any] = {}
        for item in schema["allOf"]:
            value = _schema_example(item, components, seen.copy())
            if isinstance(value, dict):
                merged.update(value)
        return merged

    if "oneOf" in schema:
        return _schema_example(schema["oneOf"][0], components, seen.copy())

    if "anyOf" in schema:
        return _schema_example(schema["anyOf"][0], components, seen.copy())

    schema_type = schema.get("type")
    if schema_type == "object" or "properties" in schema:
        result = {}
        for key, value in schema.get("properties", {}).items():
            result[key] = _schema_example(value, components, seen.copy())
        return result

    if schema_type == "array":
        return [_schema_example(schema.get("items", {}), components, seen.copy())]

    if schema_type == "string":
        schema_format = schema.get("format")
        if schema_format == "email":
            return "usuario@exemplo.com"
        if schema_format == "uuid":
            return "00000000-0000-0000-0000-000000000000"
        if schema_format == "date":
            return "2026-01-01"
        if schema_format == "date-time":
            return "2026-01-01T00:00:00Z"
        if schema_format == "password":
            return "Senha@123"
        return schema.get("default", "string")

    if schema_type == "integer":
        return schema.get("default", 0)

    if schema_type == "number":
        return schema.get("default", 0)

    if schema_type == "boolean":
        return schema.get("default", True)

    return schema.get("default", "")


def _parameter_example(parameter: dict[str, Any], components: dict[str, Any]) -> Any:
    if "example" in parameter:
        return parameter["example"]

    schema = _resolve_schema(parameter.get("schema", {}), components)
    return _schema_example(schema, components)


def _operation_requires_bearer_auth(operation: dict[str, Any]) -> bool:
    security = operation.get("security") or []
    for requirement in security:
        for scheme_name in requirement:
            if "oauth2" in scheme_name.lower() or "bearer" in scheme_name.lower():
                return True
    return False
