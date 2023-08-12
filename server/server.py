import hashlib
import os
import shutil
import time
import uuid
import zipfile

from bottle import Bottle, HTTPError, request, run

from lib.auth import auth, get_session


app = Bottle()


def validate_querystring(query: dict, check_path: str) -> tuple[str, str]:
    for name in ("id", "lmi"):
        value = query.get(name)
        if value is None:
            raise HTTPError(400, f"missing '{name}' query string parameter")
        
    request_id = query["id"]
    last_media_item_id = query["lmi"]

    if not os.path.isdir(f"{check_path}/{request_id}"):
        raise HTTPError(400, "'id' query string parameter invalid")
    
    with open(f"{check_path}/{request_id}/.last-media-item-id", "rt") as lmif:
        lmi = lmif.read()
        if lmi != last_media_item_id:
            raise HTTPError(400, "'lmi' query string parameter invalid")
        
    return (request_id, last_media_item_id)


@app.post("/upload")
def post__upload():
    response = get_session().get(
        "https://photoslibrary.googleapis.com/v1/mediaItems",
        params={"pageSize": 1}
    )

    if not response.ok:
        raise HTTPError(500, f"request to Google Photos API failed: {response.status_code} {response.reason}")
    
    response_json = response.json()
    last_media_item_id = response_json["mediaItems"][0]["id"]
    
    upload_uuid = uuid.uuid4()

    with zipfile.ZipFile(request.body, "r") as zf:
        content_hash = hashlib.sha1(request.body.read()).hexdigest()
        zf.extractall(f"dst/{upload_uuid}")

    with open(f"dst/{upload_uuid}/.last-media-item-id", "wt+") as lmif:
        lmif.truncate(0)
        lmif.write(last_media_item_id)

    response = {
        "id": str(upload_uuid),
        "hash": content_hash,
        "lmi": last_media_item_id,
    }

    return response


@app.post("/start")
def post__start():
    (request_id, _) = validate_querystring(request.query, "dst")

    shutil.move(f"dst/{request_id}", "upload/")
    with open(f"upload/{request_id}/.not-uploaded", "wt+") as nuf:
        nuf.truncate(0)
        files = list(filter(
            lambda file: not file.startswith("."), 
            os.listdir(f"upload/{request_id}")
        ))
        nuf.write("\n".join(files))

    return


@app.get("/status")
def get__status():
    (request_id, last_media_item_id) = validate_querystring(request.query, "upload")

    with open(f"upload/{request_id}/.not-uploaded", "rt") as nuf:
        filepaths = set(nuf.read().split("\n"))

    try:
        session = get_session()
        params = {"pageSize": 100}
        
        exhausted = False
        while not exhausted:
            response = session.get(
                "https://photoslibrary.googleapis.com/v1/mediaItems",
                params=params
            )

            if not response.ok:
                raise HTTPError(500, f"request to Google Photos API failed: {response.status_code} {response.reason}")

            response_json = response.json()

            if "nextPageToken" in response_json:
                params.update({"pageToken": response_json["nextPageToken"]})

            for item in response_json["mediaItems"]:
                if item["id"] == last_media_item_id:
                    exhausted = True

                filepaths.discard(item["filename"])
                if len(filepaths) == 0:
                    break

        return {
            "complete": not exhausted,
            "remaining": len(filepaths),
        }

    except Exception as e:
        with open(f"upload/{request_id}/.not-uploaded", "wt+") as nuf:
            nuf.truncate(0)
            nuf.write("\n".join(filepaths))
        raise e


if __name__ == "__main__":
    auth()
    run(app=app, host="localhost", port=43222, debug=True)