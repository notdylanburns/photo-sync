# Client

Source device

Process flow:
- `POST /upload` with zipped content -> JSON returned containing sha1 hash of received content and upload uuid
- Client validates hash
- `POST /start` with upload uuid
- `GET /status?uuid=$uuid` -> returns upload status
- Deletes the source files 

# Server

Device uploading to google photos

Process flow:
- Receives a zipped content bundle. Unzips the bundle, calculates the hash and a uuid, and returns these to client.
- Receives a start event with a uuid. Copies the bundle into the google photos upload folder
- Receives a status event with a uuid. Get a list of all 


# TODO

- Configure profile on server
- Deploy server code on server