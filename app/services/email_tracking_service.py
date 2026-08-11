import json
import os

# =========================================================
# TRACKING FILE
# =========================================================

TRACKING_FILE = os.path.join(
    "storage",
    "processed_emails.json"
)


# =========================================================
# ENSURE TRACKING FILE EXISTS
# =========================================================

def _ensure_tracking_file():
    os.makedirs(
        "storage",
        exist_ok=True
    )

    if not os.path.exists(TRACKING_FILE):

        with open(
            TRACKING_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                [],
                file
            )


# =========================================================
# GET PROCESSED EMAIL IDS
# =========================================================

def get_processed_email_ids():
    _ensure_tracking_file()

    try:

        with open(
            TRACKING_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            if isinstance(data, list):
                return data

            return []

    except (
        json.JSONDecodeError,
        OSError
    ):

        return []


# =========================================================
# CHECK WHETHER EMAIL WAS PROCESSED
# =========================================================

def is_email_processed(message_id):
    processed_ids = get_processed_email_ids()

    return message_id in processed_ids


# =========================================================
# MARK EMAIL AS PROCESSED
# =========================================================

def mark_email_processed(message_id):
    processed_ids = get_processed_email_ids()

    if message_id in processed_ids:
        return

    processed_ids.append(
        message_id
    )

    with open(
        TRACKING_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            processed_ids,
            file,
            indent=4
        )

def mark_email_processed(message_id):
    processed_ids = get_processed_email_ids()

    if message_id in processed_ids:
        return

    processed_ids.append(message_id)

    with open(
        TRACKING_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            processed_ids,
            file,
            indent=4
        )