
import subprocess

class FuelBenchError(Exception):
    pass

class RemoteTaskError(FuelBenchError):
    pass

class InvalidStateError(FuelBenchError):
    pass

class FuelServerError(FuelBenchError):
    pass

class CommandLineError(FuelBenchError):
    def __init__(self, returncode, cmd, output=None):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output
    def __str__(self):
        return "Command '%s' returned non-zero exit status %d" % (self.cmd, self.returncode)

        
__all__ = [
    'FuelBenchError',
    'RemoteTaskError',
    'InvalidStateError',
    'FuelServerError',
    'CommandLineError',
]