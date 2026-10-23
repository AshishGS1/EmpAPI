"""Error responses shared by the routers' OpenAPI documentation."""

from empapi.models.common import ErrorResponse

ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Invalid input"},
    401: {"model": ErrorResponse, "description": "Missing or invalid API key"},
    403: {"model": ErrorResponse, "description": "Your role does not allow this"},
    404: {"model": ErrorResponse, "description": "Not found"},
    422: {"model": ErrorResponse, "description": "Invalid parameters"},
    429: {"model": ErrorResponse, "description": "Rate limited"},
    502: {"model": ErrorResponse, "description": "The service failed"},
    503: {"model": ErrorResponse, "description": "The service is unavailable"},
    504: {"model": ErrorResponse, "description": "The service timed out"},
}

#employees
SEARCH_MAX_LIMIT = 50  #matched w mcp max limit
FILTER_MAX_LENGTH = 100