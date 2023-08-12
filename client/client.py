from __future__ import annotations

from lib.log import log
from lib.chunk import Chunk


class Config:
    server = "127.0.0.1"
    port = 43222


def main():
    try:
        chunks = Chunk.get_all("src")
        for chunk in chunks:
            chunk.upload(Config.server, Config.port)

    except Exception as e:
        log.error(f"program halted due to error: {e}")


if __name__ == "__main__":
    main()