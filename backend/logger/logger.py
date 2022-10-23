import logging.config

from backend.config import Config

LOGGING_LEVEL = "DEBUG" if Config.debug else "INFO"
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "default": {
            "level": LOGGING_LEVEL,
            "format": "[%(asctime)s][%(levelname)s][%(name)s][%(message)s]",
        },
        "style_transfer_metrics": {
            "level": LOGGING_LEVEL,
            "format": "[%(asctime)s][%(levelname)s]%(message)s",
        },
    },
    "handlers": {
        "default": {
            "level": LOGGING_LEVEL,
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "style_transfer_metrics": {
            "level": LOGGING_LEVEL,
            "formatter": "style_transfer_metrics",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {
            "handlers": ["default"],
            "level": LOGGING_LEVEL,
            "propagate": False,
        },
        "app.main": {
            "handlers": ["default"],
            "level": LOGGING_LEVEL,
            "propagate": False,
        },
        "backend.transfer.nst_model": {
            "handlers": ["style_transfer_metrics"],
            "level": LOGGING_LEVEL,
            "propagate": False,
        },
        "backend.transfer.transfer": {
            "handlers": ["default"],
            "level": LOGGING_LEVEL,
            "propagate": False,
        },
    },
}


logging.config.dictConfig(LOGGING_CONFIG)


loggers: dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    if name in loggers:
        return loggers[name]
    loggers[name] = logging.getLogger(name)
    return loggers[name]
