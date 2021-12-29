import click

def multi_args(*args):
    def decorator(f):
        for arg in reversed(args):
            f = arg(f)
        return f
    return decorator

course          = click.argument("course")
optional_course = click.argument("course", default="")
book            = click.argument("book")
book_label      = click.argument("book_label")
part            = click.argument("part", type=click.INT)
title           = click.argument("title")
chapter_label   = click.argument("chapter_label")
chapter_number  = click.argument("chapter_number", type=click.INT)

# Codelabs related arguments
homework           = click.argument("homework")
autograde_tar      = click.argument("autograde-tar", type=click.Path(exists=True))
autograde_makefile = click.argument("autograde-makefile", type=click.Path(exists=True))
handout            = click.argument("handout",type=click.Path(exists=True))
handin             = click.argument("handin", type=click.Path(exists=True))
