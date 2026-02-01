import argparse
import json

import requests

from test_e2e_helpers import add_server_args, start_server, wait_for_server


DEFAULT_QUESTION = "Why did you move to London?"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ask a question and inspect retrieval/Q&A output."
    )
    add_server_args(parser)
    parser.add_argument("--profile-id", required=True, help="Profile UUID")
    parser.add_argument(
        "--question",
        default=DEFAULT_QUESTION,
        help="Question to ask",
    )
    args = parser.parse_args()

    server_process = None
    if not args.no_server:
        server_process = start_server(args)
    else:
        wait_for_server(args.api, args.server_timeout)

    try:
        ask_payload = {"question": args.question}
        ask_resp = requests.post(
            f"{args.api}/api/v1/profiles/{args.profile_id}/ask",
            json=ask_payload,
            timeout=60,
        )
        ask_resp.raise_for_status()
        ask_data = ask_resp.json()

        print(json.dumps(ask_data, indent=2))
    finally:
        if server_process:
            server_process.terminate()
            server_process.wait(timeout=10)


if __name__ == "__main__":
    main()
