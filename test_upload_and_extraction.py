import argparse
import json
import time
from pathlib import Path

import requests

from test_e2e_helpers import (
    add_server_args,
    parse_list,
    prompt_if_missing,
    start_server,
    wait_for_server,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload and extract memory units.")
    add_server_args(parser)
    parser.add_argument("--profile-id", required=True, help="Profile UUID")
    parser.add_argument("--file", required=True, help="Path to file")
    parser.add_argument("--mime", required=True, help="Mime type")
    parser.add_argument("--title", help="Memory unit title")
    parser.add_argument("--description", help="Memory unit description")
    parser.add_argument("--place", action="append", help="Place (repeatable)")
    parser.add_argument("--date", action="append", help="Date (repeatable)")
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Seconds to wait for extraction results",
    )
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        raise SystemExit(f"File not found: {file_path}")

    title = prompt_if_missing(args.title, "Title")
    description = prompt_if_missing(args.description, "Description")
    places = parse_list(args.place, "Places")
    dates = parse_list(args.date, "Dates")

    server_process = None
    if not args.no_server:
        server_process = start_server(args)
    else:
        wait_for_server(args.api, args.server_timeout)

    try:
        init_payload = {
            "profile_id": args.profile_id,
            "file_name": file_path.name,
            "mime_type": args.mime,
            "bytes": file_path.stat().st_size,
        }
        init_resp = requests.post(
            f"{args.api}/api/v1/media-assets/upload-init",
            json=init_payload,
            timeout=60,
        )
        init_resp.raise_for_status()
        init_data = init_resp.json()

        upload_url = init_data["upload_url"]
        object_key = init_data["object_key"]
        object_id = init_data["object_id"]

        with file_path.open("rb") as f:
            put_resp = requests.put(
                upload_url,
                data=f,
                headers={"Content-Type": args.mime},
                timeout=300,
            )
            put_resp.raise_for_status()

        confirm_payload = {
            "profile_id": args.profile_id,
            "object_id": object_id,
            "object_key": object_key,
            "file_name": file_path.name,
            "mime_type": args.mime,
        }
        confirm_resp = requests.post(
            f"{args.api}/api/v1/media-assets/upload-confirm",
            json=confirm_payload,
            timeout=60,
        )
        confirm_resp.raise_for_status()
        confirm_data = confirm_resp.json()
        media_asset_id = confirm_data["media_asset_id"]

        deadline = time.time() + args.timeout
        last_units: list[dict] = []
        while time.time() < deadline:
            units_resp = requests.get(
                f"{args.api}/api/v1/media-assets/{media_asset_id}/memory-units",
                timeout=30,
            )
            units_resp.raise_for_status()
            units = units_resp.json()
            last_units = units
            if units:
                break
            time.sleep(3)

        if not last_units:
            raise SystemExit(
                "Timed out waiting for extraction. "
                f"Last response: {json.dumps(last_units)}"
            )

        update_payload = {
            "title": title,
            "description": description,
            "places": places,
            "dates": dates,
        }
        update_resp = requests.patch(
            f"{args.api}/api/v1/media-assets/{media_asset_id}/memory-units",
            json=update_payload,
            timeout=30,
        )
        update_resp.raise_for_status()
        updated_units = update_resp.json()

        print(
            json.dumps(
                {
                    "media_asset_id": media_asset_id,
                    "memory_units": updated_units,
                },
                indent=2,
            )
        )
    finally:
        if server_process:
            server_process.terminate()
            server_process.wait(timeout=10)


if __name__ == "__main__":
    main()
