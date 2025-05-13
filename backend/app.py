import datetime
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import os
import zipfile
from loguru import logger
from pydantic import BaseModel
from sivap import process_excel_files
from fastapi.middleware.cors import CORSMiddleware
from partial import partialRun
import re


app = FastAPI()

# Allow requests from your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Adjust if needed
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (POST, GET, etc.)
    allow_headers=["*"],  # Allow all headers
)

UPLOAD_DIR = "uploads"
AKTİVİTELER_DIR = "uploads/aktivite_raporlari"
GİRİŞ_ÇIKIŞ_DIR = "uploads/giris_cikis_verileri"
PROCESSED_DIR = "processed"
FIXED_DIR = "fixedFiles"

CUTOFF_DATE = "2222-02-22"


class DateRequest(BaseModel):
    date: str


@app.post("/set-date")
async def set_date(request: DateRequest):
    global CUTOFF_DATE

    # Regex to validate the format yyyy-mm-dd
    date_format_regex = r"^\d{4}-\d{2}-\d{2}$"

    if not re.match(date_format_regex, request.date):
        raise HTTPException(
            status_code=400, detail="Invalid date format. Expected yyyy-mm-dd"
        )

    # Update the global cutoff date
    CUTOFF_DATE = request.date
    print(f"Cutoff date set to: {CUTOFF_DATE}")

    return {"message": "Date set successfully", "date": CUTOFF_DATE}


@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(AKTİVİTELER_DIR, exist_ok=True)
    os.makedirs(GİRİŞ_ÇIKIŞ_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    try:
        file_paths = {}

        # Save uploaded files
        for file in files:
            filename = os.path.basename(file.filename)

            if filename.startswith("aktivite rap"):
                file_path = os.path.join(AKTİVİTELER_DIR, filename)
                with open(file_path, "wb") as f:
                    f.write(await file.read())
            elif filename.startswith("giris"):
                file_path = os.path.join(GİRİŞ_ÇIKIŞ_DIR, filename)
                with open(file_path, "wb") as f:
                    f.write(await file.read())
            else:
                file_path = os.path.join(UPLOAD_DIR, filename)
                with open(file_path, "wb") as f:
                    f.write(await file.read())
                file_paths[filename] = file_path

        for file in files:
            filename = os.path.basename(file.filename)
            print(f"Uploaded filename: {filename}")

        # Identify required files
        uyelik_file = file_paths.get("Effect_uyelik_sozlesmeleri.xls")
        musteriler_file = file_paths.get("Effect_musteriler.xls")
        iptal_listesi_file = file_paths.get("Effect_iptal_listesi.xls")

        for file in files:
            filename = os.path.basename(file.filename)
            print(f"Uploaded filename: {filename}")

        if not uyelik_file or not musteriler_file or not iptal_listesi_file:
            raise HTTPException(status_code=400, detail="Required files missing")

        # Read and process data
        process_excel_files(
            uyelik_file,
            musteriler_file,
            iptal_listesi_file,
            AKTİVİTELER_DIR,
            GİRİŞ_ÇIKIŞ_DIR,
            PROCESSED_DIR,
            CUTOFF_DATE,
        )

        zip_path = os.path.join(PROCESSED_DIR, "processed_files.zip")
        print(f"Zip path: {zip_path}")

        # Create the zip file
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Walk through the directory
            for root, dirs, files in os.walk(PROCESSED_DIR):
                for file in files:
                    # Full file path
                    file_path = os.path.join(root, file)

                    # Skip adding the zip file itself
                    if file_path == zip_path:
                        continue

                    # Calculate relative path
                    relative_path = os.path.relpath(file_path, PROCESSED_DIR)

                    # Add file to zip
                    print(f"Adding file: {file_path}")
                    zip_file.write(file_path, relative_path)

        print(f"Zip file created successfully at: {zip_path}")
        return FileResponse(
            zip_path, filename="processed_files.zip", media_type="application/zip"
        )
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload_excel")
async def upload_excel(file: UploadFile = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(AKTİVİTELER_DIR, exist_ok=True)
    os.makedirs(GİRİŞ_ÇIKIŞ_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    try:
        filename = os.path.basename(file.filename)

        # Validate file extension (accepts both .xls and .xlsx)
        if not (filename.endswith(".xls") or filename.endswith(".xlsx")):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Please upload an Excel file.",
            )

        # Define where to save the uploaded file (UPLOAD_DIR should be defined)
        file_path = os.path.abspath(os.path.join(UPLOAD_DIR, filename))
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Verify file saving
        if not os.path.exists(file_path):
            raise HTTPException(status_code=400, detail=f"File not saved: {file_path}")
        else:
            print(f"File saved successfully at: {file_path}")

        partialRun(file_path, PROCESSED_DIR, CUTOFF_DATE)
        zip_path = os.path.join(PROCESSED_DIR, "processed_files.zip")
        print(f"Zip path: {zip_path}")

        # Create the zip file
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Walk through the directory
            for root, dirs, files in os.walk(PROCESSED_DIR):
                for file in files:
                    # Full file path
                    file_path = os.path.join(root, file)

                    # Skip adding the zip file itself
                    if file_path == zip_path:
                        continue

                    # Calculate relative path
                    relative_path = os.path.relpath(file_path, PROCESSED_DIR)

                    # Add file to zip
                    print(f"Adding file: {file_path}")
                    zip_file.write(file_path, relative_path)

        print(f"Zip file created successfully at: {zip_path}")
        return FileResponse(
            zip_path, filename="processed_files.zip", media_type="application/zip"
        )
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload_churners")
async def upload_churners(files: list[UploadFile] = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(AKTİVİTELER_DIR, exist_ok=True)
    os.makedirs(GİRİŞ_ÇIKIŞ_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    try:
        file_paths = {}

        # Save uploaded files
        for file in files:
            filename = os.path.basename(file.filename)

            if filename.startswith("aktivite rap"):
                file_path = os.path.join(AKTİVİTELER_DIR, filename)
                with open(file_path, "wb") as f:
                    f.write(await file.read())
            elif filename.startswith("giris"):
                file_path = os.path.join(GİRİŞ_ÇIKIŞ_DIR, filename)
                with open(file_path, "wb") as f:
                    f.write(await file.read())
            else:
                file_path = os.path.join(UPLOAD_DIR, filename)
                with open(file_path, "wb") as f:
                    f.write(await file.read())
                file_paths[filename] = file_path

        for file in files:
            filename = os.path.basename(file.filename)
            print(f"Uploaded filename: {filename}")

        # Identify required files
        uyelik_file = file_paths.get("Effect_üyelik sözleşmeleri.xls")
        musteriler_file = file_paths.get("Effect_müşteriler.xls")
        iptal_listesi_file = file_paths.get("Effect_iptal listesi.xls")
        inflation_file = file_paths.get(
            "tuketici fiyat endeksi ve degisim oranlari.xls"
        )

        for file in files:
            filename = os.path.basename(file.filename)
            print(f"Uploaded filename: {filename}")

        if (
            not uyelik_file
            or not musteriler_file
            or not iptal_listesi_file
            or not inflation_file
        ):
            raise HTTPException(status_code=400, detail="Required files missing")

        # Read and process data
        process_excel_files(
            uyelik_file,
            musteriler_file,
            iptal_listesi_file,
            inflation_file,
            AKTİVİTELER_DIR,
            GİRİŞ_ÇIKIŞ_DIR,
            PROCESSED_DIR,
        )

        zip_path = os.path.join(PROCESSED_DIR, "processed_files.zip")
        print(f"Zip path: {zip_path}")

        # Create the zip file
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Walk through the directory
            for root, dirs, files in os.walk(PROCESSED_DIR):
                for file in files:
                    # Full file path
                    file_path = os.path.join(root, file)

                    # Skip adding the zip file itself
                    if file_path == zip_path:
                        continue

                    # Calculate relative path
                    relative_path = os.path.relpath(file_path, PROCESSED_DIR)

                    # Add file to zip
                    print(f"Adding file: {file_path}")
                    zip_file.write(file_path, relative_path)

        print(f"Zip file created successfully at: {zip_path}")
        return FileResponse(
            zip_path, filename="processed_files.zip", media_type="application/zip"
        )
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/show-excel")
def show_excel():
    excel_files = [
        "customer_probabilities_and_classes.xlsx",
        "logistic_regression_coefficients.xlsx",
    ]

    # Check that all files exist
    for file_name in excel_files:
        file_path = os.path.join(PROCESSED_DIR, file_name)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"{file_name} not found")

    # Create a ZIP archive containing the Excel files
    zip_path = os.path.join(PROCESSED_DIR, "excel_files.zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file_name in excel_files:
            file_path = os.path.join(PROCESSED_DIR, file_name)
            zipf.write(file_path, arcname=file_name)

    return FileResponse(
        zip_path, filename="excel_files.zip", media_type="application/zip"
    )


@app.get("/baseCustomer-excel")
def baseCustomer_excel():
    excel_file = "base_profile.xlsx"

    # Check that all files exist
    file_path = os.path.join(PROCESSED_DIR, excel_file)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"{excel_file} not found")

    # Create a ZIP archive containing the Excel files
    file_path = os.path.join(PROCESSED_DIR, "base_profile.xlsx")

    return FileResponse(
        file_path, filename="base_profile.xlsx", media_type="application/zip"
    )


@app.get("/churners-excel")
def churners_excel():
    excel_file = "comparison.xlsx"

    file_path = os.path.join(FIXED_DIR, excel_file)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"{excel_file} not found")

    file_path = os.path.join(FIXED_DIR, "comparison.xlsx")

    return FileResponse(
        file_path, filename="comparison.xlsx", media_type="application/zip"
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
