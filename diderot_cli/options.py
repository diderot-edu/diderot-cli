import click

import diderot_cli.constants as constants

def multi_opts(*opts):
    def decorator(f):
        for opt in reversed(opts):
            f = opt(f)
        return f
    return decorator

url = click.option("--url", "-a", envvar="DIDEROT_URL", default=constants.DEFAULT_DIDEROT_URL, help="Diderot API URL. For development only.")
credentials = click.option("--credentials", "-c", type=click.Path(exists=True))
username = click.option("--username", "-u", envvar="DIDEROT_USER")
password = click.option("--password", "-p", envvar="DIDEROT_PASSWORD", help="DEPRECATED. This option will be removed in future versions.")
debug = click.option("--debug/--no-debug", envvar="DEBUG", default=False, help="Shows debug messages for development.")

autograde_tar      = click.option("--autograde-tar", type=click.Path(exists=True))
autograde_makefile = click.option("--autograde-makefile", type=click.Path(exists=True))
handout            = click.option("--handout",type=click.Path(exists=True))

title           = click.option("--title")
chapter_label   = click.option("--chapter-label", type=click.STRING)
chapter_number  = click.option("--chapter-number", type=click.INT)
part_label     = click.option("--part-label", type=click.STRING)
part_number     = click.option("--part-number", type=click.INT)
publish_date    = click.option("--publish-date")
publish_on_week = click.option("--publish-on-week")

sleep_time = click.option("sleep-time", type=click.INT, default=5)

pdf           = click.option("--pdf", type=click.Path(exists=True)) # TODO(Artur): mutually exclusive with xml
xml           = click.option("--xml", type=click.Path(exists=True))
xml_pdf       = click.option("--xml-pdf", type=click.Path(exists=True))
video_url     = click.option("--video-url", type=str) # TODO(Artur): URL type
attach        = click.option("--attach", type=click.Path(exists=True), multiple=True)
sleep_time    = click.option("--sleep-time", type=click.INT, default=5)

api = multi_opts(url, credentials, username, password)
