import click

class DiderotContext:
    def __init__(self):
        self.url: str = None
        self.username: str = None
        self.password: str = None
        self.credentials: str = None
        self.debug: bool = None

        from diderot_api import DiderotClient
        self.client: DiderotClient = None

    def __repr__(self):
        return (
            f"DiderotContext(url={self.url}, username={self.username}, password={self.password},"
            f" credentials={self.credentials}, debug={self.debug})"
        )

pass_diderot_context = click.make_pass_decorator(DiderotContext)
