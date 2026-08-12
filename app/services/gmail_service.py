from googleapiclient.discovery import build
from email.mime.text import MIMEText

import base64
import re

from html import unescape


# =========================================================
# CREATE GMAIL SERVICE
# =========================================================

def create_gmail_service(credentials):

    return build(
        "gmail",
        "v1",
        credentials=credentials
    )


# =========================================================
# GMAIL PROFILE
# =========================================================

def get_gmail_profile(credentials):

    service = create_gmail_service(
        credentials
    )

    return (
        service.users()
        .get(
            userId="me"
        )
        .execute()
    )


# =========================================================
# GET RECENT INBOX EMAILS
# =========================================================

def get_recent_emails(
    credentials,
    max_results=5
):
    """
    Get recent emails from Gmail Inbox only.

    Spam, Trash, Sent, Drafts and other folders
    are ignored.
    """

    service = create_gmail_service(
        credentials
    )

    result = (
        service.users()
        .messages()
        .list(
            userId="me",
            labelIds=["INBOX"],
            maxResults=max_results
        )
        .execute()
    )

    messages = result.get(
        "messages",
        []
    )

    emails = []

    for message in messages:

        email = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message["id"],
                format="metadata",
                metadataHeaders=[
                    "From",
                    "Subject",
                    "Date"
                ]
            )
            .execute()
        )

        headers = (
            email
            .get("payload", {})
            .get("headers", [])
        )

        email_data = {
            "id": message["id"],
            "thread_id": email.get(
                "threadId"
            ),
            "from": None,
            "subject": None,
            "date": None,
            "label_ids": email.get(
                "labelIds",
                []
            ),
        }

        for header in headers:

            name = header["name"].lower()

            if name == "from":

                email_data["from"] = (
                    header["value"]
                )

            elif name == "subject":

                email_data["subject"] = (
                    header["value"]
                )

            elif name == "date":

                email_data["date"] = (
                    header["value"]
                )

        emails.append(
            email_data
        )

    return emails


# =========================================================
# CLEAN EMAIL BODY
# =========================================================

def clean_email_body(body):
    """
    Convert HTML email content
    into readable plain text.
    """

    if not body:
        return ""

    body = re.sub(
        r"<(script|style).*?>.*?</\1>",
        "",
        body,
        flags=re.IGNORECASE | re.DOTALL
    )

    body = re.sub(
        r"<img[^>]*>",
        "",
        body,
        flags=re.IGNORECASE
    )

    body = re.sub(
        r"<br\s*/?>",
        "\n",
        body,
        flags=re.IGNORECASE
    )

    body = re.sub(
        r"</(p|div|li|tr|h[1-6])>",
        "\n",
        body,
        flags=re.IGNORECASE
    )

    body = re.sub(
        r"<[^>]+>",
        "",
        body
    )

    body = unescape(
        body
    )

    body = re.sub(
        r"[ \t]+",
        " ",
        body
    )

    body = re.sub(
        r"\n\s*\n+",
        "\n\n",
        body
    )

    return body.strip()


# =========================================================
# EXTRACT EMAIL BODY
# =========================================================

def extract_email_body(payload):

    body = payload.get(
        "body",
        {}
    )

    if body.get("data"):

        decoded_body = (
            base64.urlsafe_b64decode(
                body["data"]
            )
            .decode(
                "utf-8",
                errors="ignore"
            )
        )

        return clean_email_body(
            decoded_body
        )

    for part in payload.get(
        "parts",
        []
    ):

        result = extract_email_body(
            part
        )

        if result:
            return result

    return ""


# =========================================================
# GET SINGLE EMAIL
# =========================================================

def get_email_by_id(
    credentials,
    message_id
):
    """
    Get complete Gmail email information.
    """

    service = create_gmail_service(
        credentials
    )

    email = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="full"
        )
        .execute()
    )

    payload = email.get(
        "payload",
        {}
    )

    headers = payload.get(
        "headers",
        []
    )

    email_data = {
        "id": message_id,
        "thread_id": email.get(
            "threadId"
        ),
        "from": None,
        "subject": None,
        "date": None,
        "body": extract_email_body(
            payload
        ),
        "label_ids": email.get(
            "labelIds",
            []
        ),
    }

    for header in headers:

        name = header["name"].lower()

        if name == "from":

            email_data["from"] = (
                header["value"]
            )

        elif name == "subject":

            email_data["subject"] = (
                header["value"]
            )

        elif name == "date":

            email_data["date"] = (
                header["value"]
            )

    return email_data


# =========================================================
# PREPARE EMAIL FOR AI PROCESSING
# =========================================================

def process_email(email):
    """
    Prepare Gmail email data
    for AI processing.
    """

    return {
        "message_id": email.get(
            "id"
        ),
        "thread_id": email.get(
            "thread_id"
        ),
        "from": email.get(
            "from"
        ),
        "subject": email.get(
            "subject"
        ),
        "body": email.get(
            "body"
        ),
        "label_ids": email.get(
            "label_ids",
            []
        ),
    }


# =========================================================
# CHECK WHETHER EMAIL IS IN INBOX
# =========================================================

def is_inbox_email(email):
    """
    Return True only when the Gmail
    message belongs to Inbox.
    """

    label_ids = email.get(
        "label_ids",
        []
    )

    return "INBOX" in label_ids


# =========================================================
# CREATE GMAIL DRAFT
# =========================================================

def create_gmail_draft(
    credentials,
    message_id,
    reply_body
):
    """
    Create an AI-generated reply as a Gmail Draft.

    IMPORTANT:
    This function DOES NOT send the email.

    The user must open Gmail and use
    Gmail's native Send button.
    """

    service = create_gmail_service(
        credentials
    )

    # -----------------------------------------------------
    # GET ORIGINAL EMAIL
    # -----------------------------------------------------

    original = (
        service.users()
        .messages()
        .get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=[
                "From",
                "Subject",
                "Message-ID",
                "References"
            ]
        )
        .execute()
    )

    # -----------------------------------------------------
    # VERIFY INBOX
    # -----------------------------------------------------

    label_ids = original.get(
        "labelIds",
        []
    )

    if "INBOX" not in label_ids:

        raise ValueError(
            "Only Inbox emails can be processed"
        )

    headers = (
        original
        .get("payload", {})
        .get("headers", [])
    )

    to_email = None
    subject = None
    message_id_header = None
    references = None

    # -----------------------------------------------------
    # READ ORIGINAL HEADERS
    # -----------------------------------------------------

    for header in headers:

        name = header["name"].lower()

        if name == "from":

            to_email = header["value"]

        elif name == "subject":

            subject = header["value"]

        elif name == "message-id":

            message_id_header = (
                header["value"]
            )

        elif name == "references":

            references = header["value"]

    if not to_email:

        raise ValueError(
            "Original sender email not found"
        )

    # -----------------------------------------------------
    # REPLY SUBJECT
    # -----------------------------------------------------

    reply_subject = subject or ""

    if not reply_subject.lower().startswith(
        "re:"
    ):

        reply_subject = (
            f"Re: {reply_subject}"
        )

    # -----------------------------------------------------
    # CREATE MIME MESSAGE
    # -----------------------------------------------------

    message = MIMEText(
        reply_body,
        "plain",
        "utf-8"
    )

    message["To"] = to_email
    message["Subject"] = reply_subject

    # -----------------------------------------------------
    # PRESERVE EMAIL THREAD
    # -----------------------------------------------------

    if message_id_header:

        message["In-Reply-To"] = (
            message_id_header
        )

        if references:

            message["References"] = (
                f"{references} "
                f"{message_id_header}"
            )

        else:

            message["References"] = (
                message_id_header
            )

    # -----------------------------------------------------
    # ENCODE MESSAGE
    # -----------------------------------------------------

    raw_message = (
        base64.urlsafe_b64encode(
            message.as_bytes()
        )
        .decode("utf-8")
    )

    # -----------------------------------------------------
    # CREATE GMAIL DRAFT
    # -----------------------------------------------------

    draft = (
        service.users()
        .drafts()
        .create(
            userId="me",
            body={
                "message": {
                    "raw": raw_message,
                    "threadId": original.get(
                        "threadId"
                    ),
                }
            }
        )
        .execute()
    )

    return draft


# =========================================================
# TEST EMAIL UTILITY
# =========================================================

def send_test_email(
    credentials,
    to_email,
    subject,
    body
):
    """
    Utility function for Gmail API testing.

    NOT part of the AI auto-reply workflow.
    """

    service = create_gmail_service(
        credentials
    )

    message = MIMEText(
        body,
        "plain",
        "utf-8"
    )

    message["To"] = to_email
    message["Subject"] = subject

    raw_message = (
        base64.urlsafe_b64encode(
            message.as_bytes()
        )
        .decode("utf-8")
    )

    sent_message = (
        service.users()
        .messages()
        .send(
            userId="me",
            body={
                "raw": raw_message
            }
        )
        .execute()
    )

    return sent_message

# =========================================================
# GET GMAIL DRAFTS
# =========================================================

def get_gmail_drafts(credentials):
    """
    Get all Gmail drafts.
    """

    service = create_gmail_service(
        credentials
    )

    result = (
        service.users()
        .drafts()
        .list(
            userId="me"
        )
        .execute()
    )

    drafts = result.get(
        "drafts",
        []
    )

    return drafts