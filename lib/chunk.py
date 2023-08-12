from __future__ import annotations

import hashlib
import io
import json
import os
import requests
import shutil
import time
import uuid
import zipfile

from lib.log import log


class Chunk:
    def __init__(self, files: list[str]):
        self.files = files
        self.content_hash = None
        self.last_media_item_id = None
        self.request_id = None
        self.server_url = None
        self.started = False
        self._chunkfile = f"{uuid.uuid4()}.json"

    def upload(self, server: str, port: int):
        if self.content_hash is None:
            self.server_url = f"http://{server}:{port}"
            log.info(f"using server url '{self.server_url}'")
            
            log.info("starting chunk upload")
            zipped_bytes = self._compress()
            self._dump()

        if self.request_id is None or self.last_media_item_id is None:
            retries = 0
            success = False
            while not success and retries < 5:
                log.debug(f"upload attempt {retries}")
                success = self._upload(zipped_bytes, self.server_url)
                retries += 1

            if not success:
                log.error("failed to upload chunk data")
                raise Exception()
            
            self._dump()
        
        if not self.started:
            self._start(self.server_url)
            self._dump()

        retries = 0
        complete = False
        while not complete and retries < 60:
            log.debug(f"get status attempt {retries}")
            self._status(self.server_url)
            time.sleep(60)
            retries += 1

        log.info("(re)moving uploaded files")
        self._move_uploaded_files()

        log.debug("deleting chunk file")
        self._delete()

        log.info("chunk complete")

    def _compress(self) -> bytes:
        zipped_content = io.BytesIO()
        with zipfile.ZipFile(file=zipped_content, mode="w", compresslevel=9) as zf:
            for filepath in self.files:
                arcname = filepath.removeprefix("src/")
                log.debug(f"added filepath '{arcname}'")
                zf.write(filepath, arcname=arcname)

        log.info(f"chunk compressed into {zipped_content.tell()} bytes")

        content = zipped_content.getbuffer()
        self.content_hash = hashlib.sha1(content).hexdigest()
        log.debug(f"chunk hash {self.content_hash}")

        return content
    
    def _upload(self, data: bytes, server_url: str) -> str:
        response = self._request(
            method="POST",
            url=f"{server_url}/upload",
            data=data,
            headers={
                "Content-Type": "application/octect-stream"
            }
        )

        response_json = response.json()
        self.request_id = response_json["id"]
        self.last_media_item_id = response_json["lmi"]
        content_hash = response_json["hash"]

        log.debug(f"id   = {self.request_id}")
        log.debug(f"hash = {content_hash}")
        log.debug(f"lmi  = {self.last_media_item_id}")

        if content_hash != self.content_hash:
            log.info("content hashes do not match, retrying")
            return False

        log.info("content hashes match")

        return True
    
    def _start(self, server_url: str) -> None:
        log.info(f"starting request id '{self.request_id}'")
        self._request(
            method="POST",
            url=f"{server_url}/start",
            params={
                "id": self.request_id,
                "lmi": self.last_media_item_id,
            }
        )

        self.started = True

    def _status(self, server_url: str) -> str:
        log.info(f"requesting status for '{self.request_id}'")
        response = self._request(
            method="GET",
            url=f"{server_url}/status",
            params={
                "id": self.request_id,
                "lmi": self.last_media_item_id,
            }
        )

        response_json = response.json()
        complete = response_json["complete"]
        remaining = response_json["remaining"]
        log.debug(f"complete  = {complete}")
        log.debug(f"remaining = {remaining}")
        return complete
    
    def _move_uploaded_files(self):
        files = self.files
        fileset = set(files)
        for file in files:
            new_path = os.path.join("done", file.removeprefix("src/"))
            shutil.move(file, new_path)
            fileset.discard(file)
            self._dump()
    
    def _dump(self):
        log.debug("dumping chunk state")
        with open(f"chunks/{self._chunkfile}", "wt+") as chunkf:
            json.dump({
                "_chunkfile": self._chunkfile,
                "content_hash": self.content_hash,
                "files": self.files,
                "last_media_item_id": self.last_media_item_id,
                "request_id": self.request_id,
                "server_url": self.server_url,
                "started": self.started,
            }, chunkf)

    def _delete(self):
        os.remove(self._chunkfile)

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        server_url = f"{self.server_url}/{path}"
        response = requests.request(
            method=method,
            url=server_url,
            **kwargs,
        )

        if not response.ok:
            log.error(f"request to '{server_url}' failed: {response.status_code} {response.reason}")
            return

        return response

    @classmethod
    def resume(cls, chunk_file: str):
        with open(chunk_file, "rt") as chunkf:
            chunk_info = json.load(chunkf)
            chunk = Chunk(chunk_info["files"])
            chunk._chunkfile = chunk_info["_chunkfile"]
            chunk.content_hash = chunk_info["content_hash"]
            chunk.files = chunk_info["files"]
            chunk.last_media_item_id = chunk_info["last_media_item_id"]
            chunk.request_id = chunk_info["request_id"]
            chunk.server_url = chunk_info["server_url"]
            chunk.started = chunk_info["started"]

    @classmethod
    def get_all(cls, input_dir: str, chunk_count: int = 100) -> list[Chunk]:
        chunks = []

        chunk_files = []
        input_files = sorted(os.listdir(input_dir))
        for filepath in input_files:
            qual_path = os.path.join(input_dir, filepath)

            if len(chunk_files) == chunk_count:
                chunks.append(cls(chunk_files))
                chunk_files = []
            
            chunk_files.append(qual_path)

        chunks.append(cls(chunk_files))

        return chunks
