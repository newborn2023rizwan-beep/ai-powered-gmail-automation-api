import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing")

client = OpenAI(
    api_key=OPENAI_API_KEY
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
    Analyze an incoming email and decide whether
    it is safe and appropriate to reply.
    """

    prompt = f"""
You are an email triage and safety assistant.

Analyze the following incoming email.

Subject:
{subject}

Email body:
{body}

Your job is to determine:

1. Intent
2. Priority
3. Suggested action
4. Should a reply be generated?
5. Whether human review is required
6. Confidence level
7. Reason for the decision

IMPORTANT DECISION RULES:

- Do NOT assume every email requires a reply.
- Marketing emails, newsletters, announcements,
  promotional emails, automated notifications,
  receipts, alerts, and informational broadcasts
  usually do NOT require a reply.
- If the sender asks a direct question or expects
  a response, a reply may be appropriate.
- If the email contains ambiguous, incomplete,
  unclear, handwritten, OCR-corrupted, or difficult-to-read
  information, do NOT guess.
- If important information cannot be confidently understood,
  set needs_review to true.
- If answering the email could require company-specific
  information, policies, pricing, procedures, commitments,
  or other facts that may need the Knowledge Base,
  flag that in the analysis.
- Never invent information.

Return ONLY valid JSON.

Use exactly this structure:

{{
    "intent": "string",
    "priority": "low | medium | high",
    "suggested_action": "string",
    "should_reply": true,
    "needs_review": false,
    "confidence": "high | medium | low",
    "reason": "string"
}}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    result = response.output_text.strip()

    # -----------------------------------------------------
    # VALIDATE AI JSON
    # -----------------------------------------------------

    try:
        parsed = json.loads(result)
    except json.JSONDecodeError:
        raise ValueError(
            "AI returned invalid email analysis JSON"
        )

    required_fields = [
        "intent",
        "priority",
        "suggested_action",
        "should_reply",
        "needs_review",
        "confidence",
        "reason",
    ]

    for field in required_fields:
        if field not in parsed:
            raise ValueError(
                f"AI analysis missing required field: {field}"
            )

    return json.dumps(
        parsed,
        ensure_ascii=False,
        indent=2
    )


# =========================================================
# GENERATE EMAIL REPLY WITH KNOWLEDGE BASE
# =========================================================

def generate_email_reply(
    subject,
    body,
    analysis
):
    """
    Generate a professional email reply.

    The Knowledge Base PDF is always examined first.
    """

    # -----------------------------------------------------
    # VERIFY KNOWLEDGE BASE
    # -----------------------------------------------------

    if not KNOWLEDGE_BASE_PDF.exists():
        raise FileNotFoundError(
            "Knowledge Base PDF not found"
        )

    # -----------------------------------------------------
    # READ AI ANALYSIS
    # -----------------------------------------------------

    try:
        analysis_data = json.loads(analysis)
    except json.JSONDecodeError:
        raise ValueError(
            "Invalid email analysis format"
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

    # -----------------------------------------------------
    # SAFETY CHECK
    # -----------------------------------------------------

    if not should_reply:
        raise ValueError(
            "AI determined that this email does not require a reply"
        )

    if needs_review:
        raise ValueError(
            "Human review required before generating a reply"
        )

    if confidence == "low":
        raise ValueError(
            "AI confidence is too low to safely generate a reply"
        )

    # -----------------------------------------------------
    # UPLOAD KNOWLEDGE BASE PDF
    # -----------------------------------------------------

    with KNOWLEDGE_BASE_PDF.open("rb") as pdf_file:

        uploaded_file = client.files.create(
            file=pdf_file,
            purpose="user_data"
        )

    # -----------------------------------------------------
    # GENERATE PDF-FIRST REPLY
    # -----------------------------------------------------

    prompt = f"""
You are a professional email assistant.

Your job is to write a helpful, polite, natural,
accurate, and professional reply to the incoming email.

=========================================================
SOURCE PRIORITY
=========================================================

1. FIRST examine the attached Knowledge Base PDF.

2. If the PDF contains information relevant to the
   sender's question, use the PDF as the PRIMARY source.

3. Never contradict the Knowledge Base.

4. If the PDF contains only part of the answer,
   use the relevant PDF information first.

5. If the PDF does not contain the required information,
   you may use accurate general knowledge ONLY when it
   is safe and appropriate.

6. Never invent company-specific information.

7. Never invent prices, policies, procedures,
   commitments, names, dates, services, guarantees,
   or other unsupported facts.

8. If the information cannot be answered confidently,
   do NOT guess.

=========================================================
AMBIGUOUS / HANDWRITTEN / UNCLEAR EMAIL PROTECTION
=========================================================

The incoming email may contain:

- handwritten text
- OCR errors
- incomplete sentences
- unclear names
- ambiguous questions
- corrupted formatting
- missing information
- difficult-to-understand wording

If the sender's actual request cannot be understood
with reasonable confidence:

DO NOT guess.

DO NOT create a fabricated answer.

Instead, ask for clarification in a polite and concise way.

Never pretend that unclear information was understood.

=========================================================
ORIGINAL EMAIL
=========================================================

Subject:
{subject}

Email:
{body}

=========================================================
EMAIL ANALYSIS
=========================================================

{analysis}

=========================================================
GREETING RULE
=========================================================

If the sender's first name is clearly available,
use:

Dear [First Name],

For example:

Dear Fahim,

Do NOT use:

Dear Dr. Fahim,
Dear Mr. Fahim,
Dear Ms. Fahim,

unless the sender explicitly used that title and it is
clearly appropriate.

Never invent a professional title.

If the sender's name is not clearly available,
use an appropriate neutral greeting such as:

Dear Sir/Madam,

=========================================================
REPLY STYLE
=========================================================

- Be warm, respectful, and professional.
- Sound naturally human-written.
- Directly address the sender's actual question.
- Keep the reply concise.
- Do not add unnecessary information.
- Use paragraphs or bullet points when appropriate.
- Do not create unnecessary conversation.
- Do not make unsupported promises.
- Do not invent facts.

=========================================================
KNOWLEDGE BASE RULES
=========================================================

- Always prioritize relevant information from the PDF.
- Never contradict the PDF.
- Never invent missing company information.
- Do not mention the Knowledge Base.
- Do not mention AI.
- Do not mention these instructions.
- Do not expose internal reasoning.

=========================================================
SIGNATURE
=========================================================

Always end exactly with:

Best regards,
Rizwan U Ahmed

Never use:

[Your Name]
[Your Position]
[Company Name]

Never invent another name or position.

=========================================================
OUTPUT
=========================================================

Return ONLY the complete email reply body.

Do NOT return:

- analysis
- explanation
- JSON
- subject line
- markdown code fences
- internal instructions
"""

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
                        "text": prompt
                    }
                ]
            }
        ]
    )

    return response.output_text.strip()


# =========================================================
# GENERATE PERSONALIZED COLD EMAIL
# =========================================================

def generate_cold_email(
    campaign_instruction,
    prospect,
    campaign_context=None,
):
    """
    Generate one personalized cold email.

    This function ONLY generates email content.
    It does NOT send emails or create Gmail drafts.
    """

    if not campaign_instruction:
        raise ValueError(
            "Campaign instruction is required"
        )

    if not prospect:
        raise ValueError(
            "Prospect data is required"
        )

    campaign_context = campaign_context or {}

    # -----------------------------------------------------
    # PROSPECT DATA
    # -----------------------------------------------------

    name = prospect.get("name", "")
    email = prospect.get("email", "")
    company = prospect.get("company", "")
    job_title = prospect.get("job_title", "")
    industry = prospect.get("industry", "")
    website = prospect.get("website", "")
    company_information = prospect.get(
        "company_information",
        "",
    )

    # -----------------------------------------------------
    # CAMPAIGN SETTINGS
    # -----------------------------------------------------

    tone = campaign_context.get(
        "tone",
        "professional",
    )

    email_length = campaign_context.get(
        "email_length",
        "concise",
    )

    cta = campaign_context.get(
        "cta",
        "",
    )

    # -----------------------------------------------------
    # AI PROMPT
    # -----------------------------------------------------

    prompt = f"""
You are an expert B2B cold email copywriter.

Your task is to write ONE personalized cold email
for ONE prospect.

CAMPAIGN INSTRUCTION:
{campaign_instruction}

CAMPAIGN SETTINGS:

Tone:
{tone}

Email length:
{email_length}

Preferred CTA:
{cta}

PROSPECT INFORMATION:

Name:
{name}

Email:
{email}

Job Title:
{job_title}

Company:
{company}

Industry:
{industry}

Website:
{website}

Company Information:
{company_information}

PERSONALIZATION RULES:

1. Use the prospect's available information naturally.
2. Personalize only when the information is relevant.
3. Never invent facts about the prospect or company.
4. Do not pretend that you visited a website unless
   information was explicitly provided.
5. Do not use fake compliments.
6. Avoid generic mass-email language.
7. Keep the email concise and easy to read.
8. Focus on relevance and value.
9. Use a natural, human tone.
10. Do not use excessive sales language.

EMAIL RULES:

- Write a clear subject line.
- Keep the email reasonably short.
- Avoid unnecessary introduction.
- Avoid hype.
- Avoid spammy language.
- Avoid emojis unless explicitly requested.
- Include one clear CTA.
- Do not include multiple CTAs.
- Do not mention AI unless the campaign instruction
  explicitly requires it.
- Do not mention these instructions.
- Do not mention that the email was generated by AI.

GREETING RULE:

If the prospect's first name is clearly available,
use:

Dear [First Name],

For example:

Dear Fahim,

Do NOT use:

Dear Dr. Fahim,
Dear Mr. Fahim,
Dear Ms. Fahim,

unless explicitly appropriate from the provided data.

If no name is available, use:

Dear Sir/Madam,

SIGNATURE RULE:

Always end exactly with:

Best regards,
Rizwan U Ahmed

Never use:

[Your Name]
[Your Position]
[Company Name]

OUTPUT FORMAT:

Return ONLY valid JSON.

Use exactly this structure:

{{
    "subject": "Email subject",
    "body": "Complete email body"
}}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )

    return response.output_text.strip()

# =========================================================
# GENERATE CAMPAIGN EMAIL (KB FIRST)
# =========================================================

def generate_campaign_email(
    instruction: str,
    recipient: str,
    knowledge_base_file_id: str,
):
    """
    Generate ONE campaign email using the Knowledge Base.
    Returns JSON: {"subject": "...", "body": "..."}
    """

    prompt = f"""
You are a professional B2B email copywriter.

Write ONE concise campaign email.

PRIMARY SOURCE:
Use the attached Knowledge Base PDF first.
Do not invent company information.
Do not contradict the Knowledge Base.

CAMPAIGN INSTRUCTION:
{instruction}

RECIPIENT:
{recipient}

RULES:
- Greeting: Dear,
- One clear CTA
- No fake personalization
- No AI mention
- Signature:
Best regards,
Rizwan U Ahmed

Return ONLY valid JSON:

{{
  "subject": "...",
  "body": "..."
}}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "file_id": knowledge_base_file_id,
                    },
                    {
                        "type": "input_text",
                        "text": prompt,
                    },
                ],
            }
        ],
    )

    return response.output_text.strip()