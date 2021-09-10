import click

from commands import diderot_user, diderot_admin
from context import DiderotContext

@click.group()
@click.pass_context
def diderot(ctx):
    ctx.ensure_object(DiderotContext)

diderot_admin.register_commands(diderot)
diderot_user.register_commands(diderot)
