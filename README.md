# ai-powered-gmail-automation-api

An AI-powered Gmail automation workflow that analyzes incoming emails, uses a knowledge base to generate context-aware responses, and creates Gmail drafts for human review before sending.
---
## Overview

This project automates the process of handling incoming Gmail emails with AI.

Instead of manually reading every email and writing a response, the system:

1. Detects an incoming Gmail email.
2. Reads the email content.
3. Analyzes the sender's intent and priority.
4. Uses a Knowledge Base PDF when relevant information is available.
5. Generates a professional and context-aware reply.
6. Creates the reply as a Gmail Draft.
7. Allows the user to review the generated response.
8. The user sends the final email using Gmail's native Send button.

The system does **not automatically send emails**. Human review remains the final control point.

---
## Project Purpose

The goal of this project is to reduce the time businesses spend reading and responding to repetitive emails. AI analyzes incoming Gmail messages, understands their context, and prepares personalized reply drafts based on the business's knowledge and communication needs. Instead of fully automating the final response, the workflow keeps a human in control—allowing the user to review, edit, and send the response from Gmail. This helps businesses handle email communication faster, more consistently, and with less manual effort.

---
## Technology Stack

- Python
- FastAPI
- Gmail API
- Google OAuth 2.0
- OpenAI API
- Gmail Draft API
- Python-dotenv

  ---
  
## Workflow

                Incoming Gmail Email
                         │
                         ▼
                 ┌───────────────┐
                 │  AI Analysis  │
                 └───────┬───────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ Knowledge Base / PDF│
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │ AI Response         │
              │ Generation          │
              └──────────┬──────────┘
                         │
                         ▼
                Gmail Draft Created
                         │
                         ▼
                   Human Review
                         │
                         ▼
                  Gmail Send

---

## Core Features

### Gmail OAuth Authentication

The application uses Google OAuth 2.0 to securely connect to a Gmail account.

The user authenticates through Google and the application receives the required Gmail credentials.

The project uses Gmail scopes for:

- Reading Gmail messages
- Creating Gmail drafts

---

### Gmail Email Retrieval

The system can:

- Retrieve recent Inbox emails
- Retrieve individual emails
- Read email subject, sender, date and body
- Verify whether an email belongs to the Inbox

Only Inbox emails are processed by the AI reply workflow.

---

### AI Email Analysis

Each email can first be analyzed by the AI.

The analysis identifies:

- Intent
- Priority
- Suggested action

Example:

    Intent:
    The sender is asking for information about diabetes.

    Priority:
    Medium

    Suggested Action:
    Provide a clear and concise explanation.

This analysis is then used as additional context when generating the final response.

---

## Knowledge Base Integration

The project supports a Knowledge Base PDF stored inside the project.

Example:

    storage/
    └── knowledge_base/
        └── company.pdf

The Knowledge Base is used as a source of truth when generating email responses.

The AI follows these rules:

1. Use the Knowledge Base when relevant information is available.
2. Do not invent information contained in the Knowledge Base.
3. Do not contradict the Knowledge Base.
4. If the required information is not available in the Knowledge Base, provide a reasonable generic response when appropriate.
5. Never mention the Knowledge Base or AI generation process in the email.
6. Keep the response professional, polite and concise.

This allows the system to combine company-specific knowledge with general AI capabilities.

---

## Email Reply Generation

The AI generates a professional email response based on:

- Original email subject
- Original email body
- AI analysis
- Relevant Knowledge Base information

The generated response should:

- Start with an appropriate greeting
- Directly address the sender's question
- Use clear and professional language
- Remain polite and natural
- Avoid unnecessary information
- End with the required signature

Example signature:

    Best regards,

    Rizwan U Ahmed

The AI returns only the email body so that it can be directly converted into a Gmail draft.

---

## Gmail Draft Automation

After generating the response, the application creates a Gmail Draft instead of sending the message immediately.

The draft preserves important email-thread information such as:

- Recipient
- Subject
- Message-ID
- In-Reply-To
- References
- Thread ID

This allows the generated response to remain part of the original Gmail conversation.

The user can then open Gmail, review the AI-generated response, make any required changes, and click Gmail's native **Send** button.

---

## Duplicate Processing Protection

The project includes an email tracking service to prevent the same email from being processed multiple times.

Before generating a response, the system checks whether the email has already been processed.

    Incoming Email
          │
          ▼
    Already Processed?
       │          │
      Yes         No
       │           │
       ▼           ▼
     Stop      Process Email
                  │
                  ▼
            Generate Draft
                  │
                  ▼
            Mark as Processed

Processed email IDs are tracked locally.

The tracking data is intentionally excluded from Git using `.gitignore`.

---

## Project Structure

    backend/
    │
    ├── app/
    │   │
    │   ├── api/
    │   │   ├── auth/
    │   │   │   ├── __init__.py
    │   │   │   └── google_auth.py
    │   │   │
    │   │   └── knowledge_base.py
    │   │
    │   ├── config/
    │   │   └── google/
    │   │       └── settings.py
    │   │
    │   ├── services/
    │   │   ├── ai_service.py
    │   │   ├── email_tracking_service.py
    │   │   └── gmail_service.py
    │   │
    │   └── main.py
    │
    ├── storage/
    │   └── knowledge_base/
    │       └── company.pdf
    │
    ├── .gitignore
    ├── requirements.txt
    └── README.md

---

## Main Components

### `app/main.py`

Main FastAPI application entry point.

It initializes the FastAPI application and registers the required routers.

---

### `app/api/auth/google_auth.py`

Handles the Gmail automation API workflow.

Main responsibilities include:

- Google OAuth login
- OAuth callback
- Gmail Inbox retrieval
- Individual email retrieval
- Gmail Draft retrieval
- AI reply generation
- Gmail Draft creation

Important endpoints include:

    GET  /auth/login
    GET  /auth/callback

    GET  /auth/gmail/emails
    GET  /auth/gmail/emails/{message_id}

    GET  /auth/gmail/drafts
    GET  /auth/gmail/drafts/{draft_id}

    POST /auth/gmail/emails/{message_id}/generate-draft

---

### `app/services/gmail_service.py`

Contains Gmail API operations.

Responsibilities include:

- Creating Gmail API service
- Reading Gmail profile
- Retrieving Inbox emails
- Retrieving individual emails
- Extracting email bodies
- Cleaning HTML email content
- Creating Gmail drafts

This keeps Gmail-specific logic separate from the API routes.

---

### `app/services/ai_service.py`

Contains AI-related functionality.

Responsibilities include:

- Email analysis
- AI reply generation
- Knowledge Base PDF integration
- Professional response formatting

The OpenAI API is used for AI processing.

---

### `app/services/email_tracking_service.py`

Responsible for preventing duplicate processing.

It tracks processed Gmail message IDs and ensures that an email is not processed repeatedly.

---

### `app/config/google/settings.py`

Contains Google configuration such as:

    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    GOOGLE_REDIRECT_URI

Sensitive credentials should be stored through environment variables and must never be committed to Git.

---

## API Flow

The main AI reply endpoint is:

    POST /auth/gmail/emails/{message_id}/generate-draft

The internal process is:

    Request
      │
      ▼
    Check Authentication
      │
      ▼
    Check Duplicate Processing
      │
      ▼
    Retrieve Gmail Email
      │
      ▼
    Verify Inbox
      │
      ▼
    Analyze Email with AI
      │
      ▼
    Generate Context-Aware Reply
      │
      ▼
    Create Gmail Draft
      │
      ▼
    Mark Email as Processed
      │
      ▼
    Return Draft Information

---

## Example Response

A successful draft-generation request returns information similar to:

    {
      "message": "AI reply draft created successfully",
      "original_message_id": "message-id",
      "subject": "Example Subject",
      "analysis": "AI analysis...",
      "reply": "Generated email reply...",
      "draft_id": "draft-id",
      "thread_id": "thread-id"
    }

---

## Environment Variables

Create a `.env` file for local development.

Example:

    OPENAI_API_KEY=your_openai_api_key

    GOOGLE_CLIENT_ID=your_google_client_id
    GOOGLE_CLIENT_SECRET=your_google_client_secret
    GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/auth/callback

Never commit the `.env` file to GitHub.

The project `.gitignore` excludes sensitive and local development files.

---

## Installation

Clone the repository:

    git clone https://github.com/newborn2023rizwan-beep/ai-powered-gmail-email-automation.git

Move into the project:

    cd ai-powered-gmail-email-automation

Create a virtual environment:

    python -m venv venv

Activate the virtual environment on Windows:

    venv\Scripts\activate

Install dependencies:

    pip install -r requirements.txt

Configure the `.env` file and Google OAuth credentials.

---

## Running the Application

Start the FastAPI server:

    uvicorn app.main:app --reload

The API will be available at:

    http://127.0.0.1:8000

FastAPI documentation:

    http://127.0.0.1:8000/docs

---

## Security & Human Control

This project is designed around a human-in-the-loop email workflow.

The AI can:

- Read incoming emails
- Analyze email intent
- Generate responses
- Create Gmail drafts

The AI does **not** directly send the final email.

The user remains responsible for reviewing the generated response before sending it.

This approach provides automation while maintaining human oversight.

---






