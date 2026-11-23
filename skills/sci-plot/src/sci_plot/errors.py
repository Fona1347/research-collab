class SciPlotError(Exception):
    """Base class for expected, user-facing errors."""


class ConfigurationError(SciPlotError):
    pass


class SpecError(SciPlotError):
    pass


class DataError(SciPlotError):
    pass


class SafetyError(SciPlotError):
    pass


class DependencyError(SciPlotError):
    pass


class SourceError(SciPlotError):
    pass
