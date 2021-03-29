from typing import Union


class WorkflowIdOrSecretIdConverter:
    """Convert an int workflow ID or a str workflow secret ID."""

    regex = "[1-9][0-9]{,98}|w[a-zA-Z0-9]{,99}"

    def to_python(self, value: str) -> Union[int, str]:
        if value.startswith("w"):
            return value
        else:
            return int(value)

    def to_url(self, value: Union[int, str]) -> str:
        return str(value)
