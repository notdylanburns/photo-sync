import logging

logging.basicConfig()

LOGLEVEL = logging.DEBUG

log = logging.getLogger("PhotoSync")
log.setLevel(LOGLEVEL)