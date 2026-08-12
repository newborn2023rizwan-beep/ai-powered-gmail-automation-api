from fastapi import (
    APIRouter,
    Request,
    UploadFile,
    File,
)

from fastapi.responses import JSONResponse

from pydantic import BaseModel

from google.oauth2.credentials import Credentials

import csv
import json
import re

from pathlib import Path

from app.config.google.settings import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
)

from app.api.auth.google_auth import SCOPES

from app.services.ai_service import (
    generate_campaign_email,
    client,
)

from app.services.gmail_service import (
    create_campaign_gmail_draft,
)

# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/campaign",
    tags=["Campaign"],
)


# =========================================================
# STORAGE PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

STORAGE_DIR = (
    BASE_DIR /
    "storage"
)

RECIPIENT_STORAGE_DIR = (
    STORAGE_DIR /
    "recipients"
)

RECIPIENT_CSV_FILE = (
    RECIPIENT_STORAGE_DIR /
    "recipients.csv"
)

KNOWLEDGE_BASE_PDF = (
    STORAGE_DIR /
    "knowledge_base" /
    "company.pdf"
)


# =========================================================
# CAMPAIGN REQUEST MODEL
# =========================================================

class CampaignRequest(BaseModel):

    instruction: str


# =========================================================
# EMAIL VALIDATION
# =========================================================

def is_valid_email(email: str) -> bool:

    if not email:
        return False

    pattern = (
        r"^[A-Za-z0-9._%+-]+@"
        r"[A-Za-z0-9.-]+\."
        r"[A-Za-z]{2,}$"
    )

    return bool(
        re.match(
            pattern,
            email
        )
    )


# =========================================================
# ENSURE RECIPIENT STORAGE
# =========================================================

def ensure_recipient_storage():

    RECIPIENT_STORAGE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


# =========================================================
# UPLOAD RECIPIENT CSV
# =========================================================

@router.post("/upload-recipients")
async def upload_recipients(
    file: UploadFile = File(...)
):
    """
    Upload a CSV recipient list.

    Expected CSV format:

        email
        person1@example.com
        person2@example.com
    """

    # -----------------------------------------------------
    # VALIDATE FILE TYPE
    # -----------------------------------------------------

    if not file.filename:

        return JSONResponse(
            status_code=400,
            content={
                "error": "CSV file is required"
            }
        )

    if not file.filename.lower().endswith(
        ".csv"
    ):

        return JSONResponse(
            status_code=400,
            content={
                "error": "Only CSV files are allowed"
            }
        )

    try:

        # -------------------------------------------------
        # READ FILE
        # -------------------------------------------------

        content = await file.read()

        text = content.decode(
            "utf-8-sig"
        )

        lines = text.splitlines()

        if not lines:

            return JSONResponse(
                status_code=400,
                content={
                    "error": "CSV file is empty"
                }
            )

        # -------------------------------------------------
        # PARSE CSV
        # -------------------------------------------------

        reader = csv.DictReader(
            lines
        )

        if not reader.fieldnames:

            return JSONResponse(
                status_code=400,
                content={
                    "error": "CSV header is missing"
                }
            )

        # -------------------------------------------------
        # FIND EMAIL COLUMN
        # -------------------------------------------------

        email_column = None

        for field in reader.fieldnames:

            if (
                field
                and field.strip().lower()
                == "email"
            ):

                email_column = field

                break

        if not email_column:

            return JSONResponse(
                status_code=400,
                content={
                    "error":
                        "CSV must contain an 'email' column"
                }
            )

        # -------------------------------------------------
        # PROCESS EMAILS
        # -------------------------------------------------

        valid_recipients = []

        invalid_count = 0

        for row in reader:

            email = (
                row.get(
                    email_column,
                    ""
                )
                .strip()
                .lower()
            )

            if not email:

                continue

            if is_valid_email(email):

                valid_recipients.append(
                    email
                )

            else:

                invalid_count += 1

        # -------------------------------------------------
        # REMOVE DUPLICATES
        # -------------------------------------------------

        valid_recipients = list(
            dict.fromkeys(
                valid_recipients
            )
        )

        if not valid_recipients:

            return JSONResponse(
                status_code=400,
                content={
                    "error":
                        "No valid email addresses found"
                }
            )

        # -------------------------------------------------
        # ENSURE STORAGE
        # -------------------------------------------------

        ensure_recipient_storage()

        # -------------------------------------------------
        # SAVE CSV
        # -------------------------------------------------

        with RECIPIENT_CSV_FILE.open(
            "w",
            newline="",
            encoding="utf-8"
        ) as csv_file:

            writer = csv.DictWriter(
                csv_file,
                fieldnames=["email"]
            )

            writer.writeheader()

            for email in valid_recipients:

                writer.writerow({
                    "email": email
                })

        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return {

            "message":
                "Recipient CSV uploaded successfully",

            "count":
                len(valid_recipients),

            "invalid_count":
                invalid_count,

            "file":
                str(
                    RECIPIENT_CSV_FILE
                ),
        }

    except UnicodeDecodeError:

        return JSONResponse(
            status_code=400,
            content={
                "error":
                    "CSV file must be UTF-8 encoded"
            }
        )

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "error":
                    "Failed to process recipient CSV",

                "details":
                    str(e),
            }
        )


# =========================================================
# GET STORED RECIPIENTS
# =========================================================

@router.get("/recipients")
def get_recipients():

    if not RECIPIENT_CSV_FILE.exists():

        return {
            "count": 0,
            "recipients": [],
        }

    try:

        with RECIPIENT_CSV_FILE.open(
            "r",
            encoding="utf-8"
        ) as csv_file:

            reader = csv.DictReader(
                csv_file
            )

            recipients = []

            for row in reader:

                email = (
                    row.get(
                        "email",
                        ""
                    )
                    .strip()
                    .lower()
                )

                if (
                    email
                    and is_valid_email(email)
                ):

                    recipients.append(
                        email
                    )

        # -------------------------------------------------
        # REMOVE DUPLICATES
        # -------------------------------------------------

        recipients = list(
            dict.fromkeys(
                recipients
            )
        )

        return {

            "count":
                len(recipients),

            "recipients":
                recipients,
        }

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "error":
                    "Failed to read recipient list",

                "details":
                    str(e),
            }
        )


# =========================================================
# DELETE STORED RECIPIENTS
# =========================================================

@router.delete("/recipients")
def delete_recipients():

    if not RECIPIENT_CSV_FILE.exists():

        return {
            "message":
                "No recipient list found"
        }

    try:

        RECIPIENT_CSV_FILE.unlink()

        return {

            "message":
                "Recipient list deleted successfully"
        }

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "error":
                    "Failed to delete recipient list",

                "details":
                    str(e),
            }
        )


# =========================================================
# GENERATE CAMPAIGN DRAFTS
# =========================================================

@router.post("/generate-drafts")
def generate_campaign_drafts(
    request: CampaignRequest,
    http_request: Request,
):
    """
    Generate ONE campaign email and create Gmail drafts
    in batches of maximum 250 recipients.

    Example:

        3 recipients
            -> 1 draft

        250 recipients
            -> 1 draft

        251 recipients
            -> 2 drafts

        1000 recipients
            -> 4 drafts
    """

    BATCH_SIZE = 250

    # -----------------------------------------------------
    # VALIDATE INSTRUCTION
    # -----------------------------------------------------

    instruction = (
        request.instruction.strip()
    )

    if not instruction:

        return JSONResponse(
            status_code=400,
            content={
                "error":
                    "Campaign instruction is required"
            }
        )

    # -----------------------------------------------------
    # CREATE AUTHENTICATED GMAIL CREDENTIALS
    # -----------------------------------------------------

    access_token = (
        http_request.session.get(
            "access_token"
        )
    )

    refresh_token = (
        http_request.session.get(
            "refresh_token"
        )
    )

    if not access_token:

        return JSONResponse(
            status_code=401,
            content={
                "error":
                    "Google authentication required"
            }
        )

    try:

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=(
                "https://oauth2.googleapis.com/token"
            ),
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=SCOPES,
        )

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "error":
                    "Failed to create Gmail credentials",

                "details":
                    str(e),
            }
        )

    # -----------------------------------------------------
    # LOAD RECIPIENTS FROM STORED CSV
    # -----------------------------------------------------

    if not RECIPIENT_CSV_FILE.exists():

        return JSONResponse(
            status_code=400,
            content={
                "error":
                    "No recipient list found"
            }
        )

    try:

        with RECIPIENT_CSV_FILE.open(
            "r",
            encoding="utf-8"
        ) as csv_file:

            reader = csv.DictReader(
                csv_file
            )

            stored_recipients = []

            for row in reader:

                email = (
                    row.get(
                        "email",
                        ""
                    )
                    .strip()
                    .lower()
                )

                if (
                    email
                    and is_valid_email(email)
                ):

                    stored_recipients.append(
                        email
                    )

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "error":
                    "Failed to read recipient list",

                "details":
                    str(e),
            }
        )

    # -----------------------------------------------------
    # REMOVE DUPLICATES
    # -----------------------------------------------------

    cleaned_recipients = list(
        dict.fromkeys(
            stored_recipients
        )
    )

    if not cleaned_recipients:

        return JSONResponse(
            status_code=400,
            content={
                "error":
                    "No valid recipients found"
            }
        )

    # -----------------------------------------------------
    # CHECK KNOWLEDGE BASE
    # -----------------------------------------------------

    if not KNOWLEDGE_BASE_PDF.exists():

        return JSONResponse(
            status_code=400,
            content={
                "error":
                    "Knowledge Base PDF not found",

                "path":
                    str(
                        KNOWLEDGE_BASE_PDF
                    ),
            }
        )

    try:

        # -------------------------------------------------
        # UPLOAD KNOWLEDGE BASE PDF
        # -------------------------------------------------

        with KNOWLEDGE_BASE_PDF.open(
            "rb"
        ) as pdf_file:

            uploaded_file = (
                client.files.create(
                    file=pdf_file,
                    purpose="user_data",
                )
            )

        # -------------------------------------------------
        # GENERATE ONE CAMPAIGN EMAIL
        # -------------------------------------------------

        # IMPORTANT:
        #
        # AI generates the campaign email
        # ONLY ONCE.
        #
        # We do NOT generate one email
        # per recipient or per batch.

        campaign_email_json = (
            generate_campaign_email(
                instruction=instruction,
                recipient="Campaign recipients",
                knowledge_base_file_id=(
                    uploaded_file.id
                ),
            )
        )

        # -------------------------------------------------
        # PARSE AI RESPONSE
        # -------------------------------------------------

        try:

            email_data = json.loads(
                campaign_email_json
            )

        except json.JSONDecodeError:

            raise ValueError(
                "AI returned invalid JSON"
            )

        # -------------------------------------------------
        # GET SUBJECT
        # -------------------------------------------------

        subject = (
            email_data.get(
                "subject",
                ""
            )
            .strip()
        )

        # -------------------------------------------------
        # GET BODY
        # -------------------------------------------------

        body = (
            email_data.get(
                "body",
                ""
            )
            .strip()
        )

        if not subject:

            raise ValueError(
                "AI returned empty subject"
            )

        if not body:

            raise ValueError(
                "AI returned empty body"
            )

        # -------------------------------------------------
        # CREATE RECIPIENT BATCHES
        # -------------------------------------------------

        batches = [

            cleaned_recipients[
                i:i + BATCH_SIZE
            ]

            for i in range(
                0,
                len(cleaned_recipients),
                BATCH_SIZE
            )
        ]

        # -------------------------------------------------
        # CREATE ONE GMAIL DRAFT PER BATCH
        # -------------------------------------------------

        drafts = []

        for index, batch in enumerate(
            batches,
            start=1
        ):

            # -------------------------------------------------
            # FIRST RECIPIENT → TO
            # REMAINING → BCC
            # -------------------------------------------------

            to_email = batch[0]

            bcc_emails = batch[1:]

            # -------------------------------------------------
            # CREATE GMAIL DRAFT
            # -------------------------------------------------

            draft = (
                create_campaign_gmail_draft(
                    credentials=credentials,
                    to_email=to_email,
                    bcc_emails=bcc_emails,
                    subject=subject,
                    body=body,
                )
            )

            # -------------------------------------------------
            # EXTRACT GMAIL IDS
            # -------------------------------------------------

            message_data = draft.get(
                "message",
                {}
            )

            drafts.append({

                "batch_number":
                    index,

                "recipient_count":
                    len(batch),

                "to":
                    to_email,

                "bcc_count":
                    len(bcc_emails),

                "recipients":
                    batch,

                "subject":
                    subject,

                "draft_id":
                    draft.get(
                        "id"
                    ),

                "message_id":
                    message_data.get(
                        "id"
                    ),

                "thread_id":
                    message_data.get(
                        "threadId"
                    ),
            })

        # -------------------------------------------------
        # FINAL RESPONSE
        # -------------------------------------------------

        return {

            "message":
                "Campaign drafts created successfully",

            "instruction":
                instruction,

            "recipient_count":
                len(cleaned_recipients),

            "batch_size":
                BATCH_SIZE,

            "batch_count":
                len(batches),

            "generated_count":
                1,

            "draft_count":
                len(drafts),

            "subject":
                subject,

            "drafts":
                drafts,
        }

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "error":
                    "Failed to generate campaign emails",

                "details":
                    str(e),
            }
        )