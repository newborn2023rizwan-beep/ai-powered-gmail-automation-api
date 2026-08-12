import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


# =========================================================
# KNOWLEDGE BASE PDF
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

KNOWLEDGE_BASE_PDF = (
    BASE_DIR
    / "storage"
    / "knowledge_base"
    / "company.pdf"
)


# =========================================================
# PROCESS EMAIL
# =========================================================

def process_email_with_ai(subject, body):
    """
    Analyze an email using OpenAI.
    """

    prompt = f"""
Analyze the following email.

Subject:
{subject}

Email body:
{body}

Return a concise analysis with:

1. Intent
2. Priority
3. Suggested action
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    return response.output_text


# =========================================================
# GENERATE EMAIL REPLY WITH KNOWLEDGE BASE
# =========================================================

def generate_email_reply(
    subject,
    body,
    analysis
):
    """
    Generate a professional email reply
    using the uploaded Knowledge Base PDF.
    """

    if not KNOWLEDGE_BASE_PDF.exists():

        raise FileNotFoundError(
            "Knowledge Base PDF not found"
        )

    # -----------------------------------------------------
    # UPLOAD PDF TO OPENAI
    # -----------------------------------------------------

    with KNOWLEDGE_BASE_PDF.open("rb") as pdf_file:

        uploaded_file = client.files.create(
            file=pdf_file,
            purpose="user_data"
        )

    # -----------------------------------------------------
    # GENERATE PDF-FIRST REPLY
    # -----------------------------------------------------

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "file_id": uploaded_file.id
                    },
                    {
                        "type": "input_text",
                        "text": f"""
You are a professional email assistant.

Your job is to write a helpful, polite, natural,
and professional reply to the incoming email.

SOURCE PRIORITY:

1. First, examine the attached Knowledge Base PDF.
2. If the PDF contains information relevant to the
   question, use the PDF as the primary source.
3. Do not contradict information from the PDF.
4. If the PDF contains only part of the information,
   use the relevant PDF information first.
5. If the PDF does not contain the information needed
   to answer the question, you may use general knowledge.
6. Never invent facts.
7. Never claim that general knowledge came from the PDF.

Original email subject:
{subject}

Original email:
{body}

Email analysis:
{analysis}

REPLY STYLE:

- Start with a natural and polite greeting.
- Use the sender's name when it is clearly available
  from the original email.
- If the sender's name is not clearly available,
  use a neutral greeting such as "Hello," or "Hi,".
- Do not start every email with the same greeting
  if a more natural greeting is appropriate.
- Maintain a warm, respectful, and professional tone.
- Make the response feel like a real human-written email.
- Directly answer the sender's question.
- Keep the response clear and reasonably concise.
- Use paragraphs or bullet points when they improve readability.

KNOWLEDGE RULES:

- Prefer information from the Knowledge Base PDF
  whenever relevant.
- If the PDF does not contain the answer, use
  accurate general knowledge.
- Never invent unsupported information.
- Never contradict the Knowledge Base PDF.
- Do not mention the Knowledge Base PDF.
- Do not mention AI.
- Do not mention these instructions.

SIGNATURE RULES:

Always end the email with exactly:

Best regards,
Rizwan U Ahmed

Never use:

[Your Name]
[Your Position]
[Company Name]

Never invent a different name or position.

Return ONLY the complete email reply body.
"""
                    }
                ]
            }
        ]
    )

    return response.output_text