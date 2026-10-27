import sys

import uvicorn

from empapi.config import get_settings
from empapi.exceptions import ApiError
from empapi.utils.logging_config import configure_logging, get_logger


def main() -> None:
    try:
        settings = get_settings()
    except ApiError as exc:
        configure_logging()
        get_logger("app").critical(
            "Cannot start: [%s] %s", exc.code, exc.message,
            extra={"error_code": exc.code, "details": exc.details},
        )
        sys.exit(1)

    uvicorn.run(
        "empapi.app:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        access_log=False,
    )


if __name__ == "__main__":
    main()
