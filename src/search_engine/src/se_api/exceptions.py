class SeAPIException(Exception):
    msg: str

    def __init__(self, msg: str, *args: object) -> None:
        self.msg = msg
        super().__init__(*args)
