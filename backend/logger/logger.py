import logging.config

from backend.config import Config


LOGGING_LEVEL = "DEBUG" if Config.debug else "INFO"
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "default": {
            "format": "[%(asctime)s][%(levelname)s][%(name)s][%(message)s]",
        },
        "app_router_formatter": {
            "format": "[%(asctime)s][%(levelname)s][%(name)s][%(username)s][%(message)s]",
        },
        "backend_nst_model_loss_formatter": {
            "format": "[%(asctime)s][%(levelname)s][%(name)s][%(username)s][content: %(content_loss).3f][style: %(style_loss).3f]"
                      "[total: %(total_loss).3f]"
        },
        "backend_transfer_formatter": {
            "format": "[%(asctime)s][%(levelname)s][%(name)s][%(username)s][%(message)s]",
        }
    },
    "handlers": {
        "default": {
            "level": LOGGING_LEVEL,
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "app_handler": {
            "level": LOGGING_LEVEL,
            "formatter": "app_router_formatter",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "backend_nst_model_handler": {
            "level": LOGGING_LEVEL,
            "formatter": "backend_nst_model_loss_formatter",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "backend_transfer_handler": {
            "level": LOGGING_LEVEL,
            "formatter": "backend_transfer_formatter",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        }
    },
    "loggers": {
        "": {
            "handlers": ["default"],
            "level": LOGGING_LEVEL,
            "propagate": False,
        },
        "app.routes": {
            "handlers": ["app_handler"],
            "level": LOGGING_LEVEL,
            "propagate": False,
        },
        "app.controllers": {
            "handlers": ["app_handler"],
            "level": LOGGING_LEVEL,
            "propagate": False,
        },
        "backend.transfer.nst_model": {
            "handlers": ["backend_nst_model_handler"],
            "level": LOGGING_LEVEL,
            "propagate": False,
        },
        "backend.transfer.transfer": {
            "handlers": ["backend_transfer_handler"],
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
