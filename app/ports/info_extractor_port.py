from typing import Protocol


class InfoExtractorPort(Protocol):
    def extract(self, ocr_text: str) -> dict:
        ...
