from typing import Protocol, Dict, Any


class Parser(Protocol):
    def parse(self, text: str) -> Dict[str, Any]:
        """Parse input text and return a dict of extracted values."""
        ...
