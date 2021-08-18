import argparse

class Formatter(argparse.HelpFormatter):
    """Custom formatter for argparse which displays all positional arguments first."""
    # Use defined argument order to display usage.
    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            prefix = "usage: "

        # If usage is specified, use that.
        if usage is not None:
            usage = usage % dict(prog=self._prog)

        # If no optionals or positionals are available, usage is just prog.
        elif usage is None and not actions:
            usage = "%(prog)s" % dict(prog=self._prog)
        elif usage is None:
            prog = "%(prog)s" % dict(prog=self._prog)
            # Build full usage string.
            action_usage = self._format_actions_usage(actions, groups)  # NEW
            usage = " ".join([s for s in [prog, action_usage] if s])
            # Omit the long line wrapping code.
        # Prefix with 'usage:'.
        return "%s%s\n\n" % (prefix, usage)
