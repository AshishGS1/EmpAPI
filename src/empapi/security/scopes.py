"""Scopes and roles."""



SCOPE_EMPLOYEES_READ = "employees:read"
SCOPE_DEPARTMENTS_READ = "departments:read"
SCOPE_SALARY_READ = "salary:read"

ROLE_SCOPES: dict[str, frozenset[str]] = {
    "viewer": frozenset({SCOPE_EMPLOYEES_READ}),
    "analyst": frozenset({SCOPE_EMPLOYEES_READ, SCOPE_DEPARTMENTS_READ}),
    "hr": frozenset({SCOPE_EMPLOYEES_READ, SCOPE_DEPARTMENTS_READ, SCOPE_SALARY_READ}),
}

ROLES = tuple(ROLE_SCOPES)


def scopes_for_role(role: str) -> frozenset[str] | None:
    """The role's scopes, or None for a role this code does not know (fail closed)."""
    return ROLE_SCOPES.get(role)
