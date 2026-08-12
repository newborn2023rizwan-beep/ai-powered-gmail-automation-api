from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials

from app.config.google.settings import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
)

from app.services.ai_service import (
    process_email_with_ai,
    generate_email_reply,
)

from app.services.gmail_service import (
    get_email_by_id,
    create_gmail_service,
    create_gmail_draft,
    get_gmail_drafts,
)

from app.services.email_tracking_service import (
    is_email_processed,
    mark_email_processed,
)

router = APIRouter(
    prefix="/auth",
    tags=["Google Auth"],
)

# =========================================================
# GOOGLE SCOPES
# =========================================================

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]

# =========================================================
# CREATE GOOGLE OAUTH FLOW
# =========================================================

def create_flow():

    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                GOOGLE_REDIRECT_URI
            ],
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )

    return flow


# =========================================================
# GOOGLE LOGIN
# =========================================================

@router.get("/login")
def google_login(request: Request):

    flow = create_flow()

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    request.session["oauth_state"] = state
    request.session["oauth_code_verifier"] = flow.code_verifier

    return RedirectResponse(
        url=authorization_url
    )


# =========================================================
# GOOGLE CALLBACK
# =========================================================

@router.get("/callback")
def google_callback(
    request: Request,
    code: str,
    state: str,
):

    saved_state = request.session.get(
        "oauth_state"
    )

    saved_code_verifier = request.session.get(
        "oauth_code_verifier"
    )

    if not saved_state:

        return JSONResponse(
            status_code=400,
            content={
                "error": "OAuth state not found",
            },
        )

    if state != saved_state:

        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid OAuth state",
            },
        )

    if not saved_code_verifier:

        return JSONResponse(
            status_code=400,
            content={
                "error": "OAuth code verifier not found",
            },
        )

    flow = create_flow()

    flow.code_verifier = saved_code_verifier

    try:

        flow.fetch_token(
            code=code
        )

        credentials = flow.credentials

        request.session["access_token"] = credentials.token
        request.session["refresh_token"] = credentials.refresh_token

        request.session.pop(
            "oauth_state",
            None
        )

        request.session.pop(
            "oauth_code_verifier",
            None
        )

        return RedirectResponse(
            url="/"
        )

    except Exception as e:

        return JSONResponse(
            status_code=400,
            content={
                "error": "Google authentication failed",
                "details": str(e),
            },
        )


# =========================================================
# GET GMAIL INBOX EMAILS
# =========================================================

@router.get("/gmail/emails")
def get_gmail_emails(
    request: Request,
):

    access_token = request.session.get(
        "access_token"
    )

    refresh_token = request.session.get(
        "refresh_token"
    )

    if not access_token:

        return JSONResponse(
            status_code=401,
            content={
                "error": "Google authentication required",
            },
        )

    try:

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=SCOPES,
        )

        service = create_gmail_service(
            credentials
        )

        result = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=["INBOX"],
                maxResults=10,
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
                        "Date",
                    ],
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
                "from": None,
                "subject": None,
                "date": None,
            }

            for header in headers:

                name = header["name"].lower()

                if name == "from":

                    email_data["from"] = header["value"]

                elif name == "subject":

                    email_data["subject"] = header["value"]

                elif name == "date":

                    email_data["date"] = header["value"]

            emails.append(
                email_data
            )

        return {
            "count": len(emails),
            "emails": emails,
        }

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to fetch Gmail inbox",
                "details": str(e),
            },
        )


# =========================================================
# GET SINGLE GMAIL EMAIL
# =========================================================

@router.get("/gmail/emails/{message_id}")
def get_single_gmail_email(
    message_id: str,
    request: Request,
):

    access_token = request.session.get(
        "access_token"
    )

    refresh_token = request.session.get(
        "refresh_token"
    )

    if not access_token:

        return JSONResponse(
            status_code=401,
            content={
                "error": "Google authentication required",
            },
        )

    try:

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=SCOPES,
        )

        email = get_email_by_id(
            credentials=credentials,
            message_id=message_id,
        )

        return email

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to fetch email",
                "details": str(e),
            },
        )


# =========================================================
# GET GMAIL DRAFTS
# =========================================================

@router.get("/gmail/drafts")
def get_gmail_drafts_endpoint(
    request: Request,
):

    access_token = request.session.get(
        "access_token"
    )

    refresh_token = request.session.get(
        "refresh_token"
    )

    if not access_token:

        return JSONResponse(
            status_code=401,
            content={
                "error": "Google authentication required",
            },
        )

    try:

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=SCOPES,
        )

        drafts = get_gmail_drafts(
            credentials
        )

        return {
            "count": len(drafts),
            "drafts": drafts,
        }

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to fetch Gmail drafts",
                "details": str(e),
            },
        )


# =========================================================
# GET SINGLE GMAIL DRAFT
# =========================================================

@router.get("/gmail/drafts/{draft_id}")
def get_single_gmail_draft(
    draft_id: str,
    request: Request,
):

    access_token = request.session.get(
        "access_token"
    )

    refresh_token = request.session.get(
        "refresh_token"
    )

    if not access_token:

        return JSONResponse(
            status_code=401,
            content={
                "error": "Google authentication required",
            },
        )

    try:

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=SCOPES,
        )

        service = create_gmail_service(
            credentials
        )

        draft = (
            service.users()
            .drafts()
            .get(
                userId="me",
                id=draft_id,
                format="full",
            )
            .execute()
        )

        return draft

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to fetch Gmail draft",
                "details": str(e),
            },
        )


# =========================================================
# GENERATE GMAIL DRAFT
# =========================================================

@router.post("/gmail/emails/{message_id}/generate-draft")
def generate_gmail_draft(
    message_id: str,
    request: Request,
):

    access_token = request.session.get(
        "access_token"
    )

    refresh_token = request.session.get(
        "refresh_token"
    )

    if not access_token:

        return JSONResponse(
            status_code=401,
            content={
                "error": "Google authentication required",
            },
        )

    try:

        # -------------------------------------------------
        # DUPLICATE CHECK
        # -------------------------------------------------

        if is_email_processed(message_id):

            return JSONResponse(
                status_code=400,
                content={
                    "error": "This email has already been processed"
                },
            )

        # -------------------------------------------------
        # CREATE CREDENTIALS
        # -------------------------------------------------

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=SCOPES,
        )

        # -------------------------------------------------
        # GET EMAIL
        # -------------------------------------------------

        email = get_email_by_id(
            credentials=credentials,
            message_id=message_id,
        )

        # -------------------------------------------------
        # VERIFY EMAIL IS IN INBOX
        # -------------------------------------------------

        service = create_gmail_service(
            credentials
        )

        gmail_message = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="metadata",
            )
            .execute()
        )

        labels = gmail_message.get(
            "labelIds",
            []
        )

        if "INBOX" not in labels:

            return JSONResponse(
                status_code=400,
                content={
                    "error": "Only Inbox emails can be processed",
                },
            )

        # -------------------------------------------------
        # AI ANALYSIS + REPLY DECISION
        # -------------------------------------------------

        analysis = process_email_with_ai(
            subject=email.get("subject", ""),
            body=email.get("body", ""),
        )

        # -------------------------------------------------
        # PARSE AI DECISION
        # -------------------------------------------------

        import json

        try:

            analysis_data = json.loads(analysis)

        except json.JSONDecodeError:

            return JSONResponse(
                status_code=500,
                content={
                    "error": "AI returned invalid analysis format",
                    "details": analysis,
                },
            )

        should_reply = analysis_data.get(
            "should_reply",
            False
        )

        needs_review = analysis_data.get(
            "needs_review",
            True
        )

        confidence = analysis_data.get(
            "confidence",
            "low"
        )

        # -------------------------------------------------
        # DO NOT REPLY
        # -------------------------------------------------

        if not should_reply:

            return {
                "message": "No reply required",
                "draft_created": False,
                "original_message_id": message_id,
                "analysis": analysis_data,
            }

        # -------------------------------------------------
        # HUMAN REVIEW REQUIRED
        # -------------------------------------------------

        if needs_review:

            return {
                "message": "Human review required",
                "draft_created": False,
                "original_message_id": message_id,
                "analysis": analysis_data,
            }

        # -------------------------------------------------
        # LOW CONFIDENCE
        # -------------------------------------------------

        if confidence == "low":

            return {
                "message": "AI confidence is too low",
                "draft_created": False,
                "original_message_id": message_id,
                "analysis": analysis_data,
            }

        # -------------------------------------------------
        # GENERATE AI REPLY
        # -------------------------------------------------

        reply = generate_email_reply(
            subject=email.get("subject", ""),
            body=email.get("body", ""),
            analysis=analysis,
        )

        # -------------------------------------------------
        # CREATE GMAIL DRAFT
        # -------------------------------------------------

        draft = create_gmail_draft(
            credentials=credentials,
            message_id=message_id,
            reply_body=reply,
        )

        # -------------------------------------------------
        # MARK EMAIL AS PROCESSED
        # -------------------------------------------------

        mark_email_processed(
            message_id
        )

        # -------------------------------------------------
        # FINAL RESPONSE
        # -------------------------------------------------

        return {
            "message": "AI reply draft created successfully",
            "draft_created": True,
            "original_message_id": message_id,
            "subject": email.get("subject"),
            "analysis": analysis_data,
            "reply": reply,
            "draft_id": draft.get("id"),
            "thread_id": draft.get(
                "message",
                {}
            ).get("threadId"),
        }

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to generate Gmail draft",
                "details": str(e),
            },
        )