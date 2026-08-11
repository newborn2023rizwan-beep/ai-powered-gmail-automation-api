from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import shutil


router = APIRouter(
    prefix="/knowledge-base",
    tags=["Knowledge Base"],
)


# =========================================================
# STORAGE
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

STORAGE_DIR = (
    BASE_DIR
    / "storage"
    / "knowledge_base"
)

STORAGE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

PDF_FILE = STORAGE_DIR / "company.pdf"


# =========================================================
# UPLOAD PDF
# =========================================================

@router.post("/upload")
def upload_knowledge_base(
    file: UploadFile = File(...)
):

    # -----------------------------------------------------
    # VALIDATE FILE TYPE
    # -----------------------------------------------------

    if file.content_type != "application/pdf":

        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )

    # -----------------------------------------------------
    # REMOVE EXISTING PDF
    # -----------------------------------------------------

    if PDF_FILE.exists():

        PDF_FILE.unlink()

    # -----------------------------------------------------
    # SAVE NEW PDF
    # -----------------------------------------------------

    try:

        with PDF_FILE.open("wb") as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Failed to save PDF: {str(e)}"
        )

    return {
        "message": "Knowledge Base PDF uploaded successfully",
        "filename": file.filename,
        "path": str(PDF_FILE),
    }


# =========================================================
# GET CURRENT KNOWLEDGE BASE
# =========================================================

@router.get("/")
def get_knowledge_base():

    if not PDF_FILE.exists():

        return {
            "exists": False,
            "filename": None,
        }

    return {
        "exists": True,
        "filename": "company.pdf",
        "path": str(PDF_FILE),
    }


# =========================================================
# DELETE KNOWLEDGE BASE
# =========================================================

@router.delete("/")
def delete_knowledge_base():

    if not PDF_FILE.exists():

        return {
            "message": "No Knowledge Base PDF found"
        }

    try:

        PDF_FILE.unlink()

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete PDF: {str(e)}"
        )

    return {
        "message": "Knowledge Base PDF deleted successfully"
    }