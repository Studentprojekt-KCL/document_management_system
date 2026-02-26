"""Copyright (c) 2026, Studentprojekt Knowit Cybersecurity and Law"""


class SeAPIException(Exception):
    """Search Engine Exception.

    Attributes:
        msg: error message.
    """

    msg: str

    def __init__(self, msg: str, *args: object) -> None:
        self.msg = msg
        super().__init__(*args)
