from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
import time
from typing import List
import json
import uuid

from fastapi.responses import StreamingResponse
import zipfile
from io import BytesIO
from datetime import datetime

# Import our existing production engines
from ai_extractor import AIExtractor
from vision_processor import VisionProcessor
from excel_export import ExcelExporter
from tally_xml import TallyExporter
from local_scanner import LocalScanner
from outlook_fetcher import OutlookFetcher
from groq import Groq

from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Infinx AP Tracker API")

# Ensure the data directory exists before mounting
os.makedirs("data", exist_ok=True)

# Mount data for static file access (exports/uploads)
app.mount("/data", StaticFiles(directory="data"), name="data")

# Setup CORS for React development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines
extractor = AIExtractor()
processor = VisionProcessor()
excel_gen = ExcelExporter()
tally_gen = TallyExporter()
scanner = LocalScanner(watch_dir="data/local_import")
fetcher = OutlookFetcher()

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory session store
invoice_registry = []
app_config = {
    "groq_key": os.getenv("GROQ_API_KEY", ""),
    "email": os.getenv("OUTLOOK_EMAIL", ""),
    "password": os.getenv("OUTLOOK_PASSWORD", ""),
    "model_name": "meta-llama/llama-4-scout-17b-16e-instruct"
}

@app.get("/api/config")
async def get_config():
    return app_config

@app.post("/api/config")
async def update_config(config: dict):
    app_config.update(config)
    # Re-initialize extractor if key changed
    if "groq_key" in config:
        extractor.api_key = config["groq_key"]
        extractor.client = Groq(api_key=extractor.api_key)
    return {"status": "success"}

@app.get("/api/invoices")
async def get_invoices():
    return invoice_registry

async def run_extraction_worker(doc_id: str, file_path: str, filename: str):
    """Background worker that performs the heavy LLM lifting."""
    try:
        image_paths = processor.prepare_file(file_path)
        if not image_paths:
            # Update status to failed
            for inv in invoice_registry:
                if inv["id"] == doc_id:
                    inv["status"] = "Failed"
                    inv["vendor"] = "Unsupported Format"
            return

        data = extractor.extract_invoice_data(image_paths)
        
        # Update registry in-place
        for inv in invoice_registry:
            if inv["id"] == doc_id:
                if "error" in data:
                    inv["status"] = "Failed"
                    inv["vendor"] = "AI Error"
                else:
                    inv.update({
                        "vendor": data.get("vendor_name") or "Unknown",
                        "vendor_gst": data.get("vendor_tax_id") or "N/A",
                        "invoice_no": data.get("invoice_number") or "N/A",
                        "po_number": data.get("po_number") or "N/A",
                        "date": data.get("invoice_date") or "N/A",
                        "total": data.get("total_amount") or 0.0,
                        "status": "Uploaded",
                        "raw_data": data
                    })
                break
    except Exception as e:
        print(f"Background Extraction Worker Error: {e}")
        for inv in invoice_registry:
            if inv["id"] == doc_id:
                inv["status"] = "Failed"
                inv["vendor"] = "System Error"
                break

@app.post("/api/extract")
async def extract_invoice(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Initialize placeholder in registry
    doc_id = f"{int(time.time())}_{uuid.uuid4().hex[:6]}_{file.filename}"
    new_item = {
        "id": doc_id,
        "filename": file.filename,
        "vendor": "Processing...",
        "vendor_gst": "N/A",
        "invoice_no": "N/A",
        "po_number": "N/A",
        "date": "N/A",
        "total": 0.0,
        "status": "Processing",
        "assigned_hod": "Unassigned",
        "raw_data": {},
        "file_path": file_path,
        "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    invoice_registry.insert(0, new_item) # Add to top of list
    
    # Offload extraction to background
    background_tasks.add_task(run_extraction_worker, doc_id, file_path, file.filename)
    
    return new_item

@app.post("/api/approve/{invoice_id}")
async def approve_invoice(invoice_id: str):
    for inv in invoice_registry:
        if inv["id"] == invoice_id:
            inv["status"] = "Approved"
            return {"status": "success"}
    raise HTTPException(status_code=404, detail="Invoice not found")

@app.post("/api/reject/{invoice_id}")
async def reject_invoice(invoice_id: str):
    for inv in invoice_registry:
        if inv["id"] == invoice_id:
            inv["status"] = "Rejected"
            return {"status": "success"}
    raise HTTPException(status_code=404, detail="Invoice not found")

@app.post("/api/pay/{invoice_id}")
async def pay_invoice(invoice_id: str):
    for inv in invoice_registry:
        if inv["id"] == invoice_id:
            inv["status"] = "Paid"
            return {"status": "success"}
    raise HTTPException(status_code=404, detail="Invoice not found")

@app.delete("/api/invoices")
async def clear_all_invoices():
    global invoice_registry
    invoice_registry = []
    return {"status": "success"}

@app.delete("/api/invoices/{invoice_id}")
async def delete_invoice(invoice_id: str):
    global invoice_registry
    before_len = len(invoice_registry)
    invoice_registry = [i for i in invoice_registry if i["id"] != invoice_id]
    if len(invoice_registry) < before_len:
        return {"status": "success"}
    raise HTTPException(status_code=404, detail="Invoice not found")

@app.post("/api/sync/local")
async def sync_local(background_tasks: BackgroundTasks):
    files = scanner.scan_and_move()
    for f in files:
        doc_id = f"{int(time.time())}_{uuid.uuid4().hex[:6]}_{f['filename']}"
        new_item = {
            "id": doc_id,
            "filename": f["filename"],
            "vendor": "Processing...",
            "vendor_gst": "N/A",
            "invoice_no": "N/A",
            "po_number": "N/A",
            "date": "N/A",
            "total": 0.0,
            "status": "Processing",
            "assigned_hod": "Unassigned",
            "raw_data": {},
            "file_path": f["path"],
            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        invoice_registry.insert(0, new_item)
        background_tasks.add_task(run_extraction_worker, doc_id, f["path"], f["filename"])
    return {"status": "success", "count": len(files)}

@app.post("/api/sync/email")
async def sync_email(background_tasks: BackgroundTasks):
    files = fetcher.fetch_attachments()
    for f in files:
        doc_id = f"{int(time.time())}_{uuid.uuid4().hex[:6]}_{f['filename']}"
        new_item = {
            "id": doc_id,
            "filename": f["filename"],
            "vendor": "Processing...",
            "vendor_gst": "N/A",
            "invoice_no": "N/A",
            "po_number": "N/A",
            "date": "N/A",
            "total": 0.0,
            "status": "Processing",
            "assigned_hod": "Unassigned",
            "raw_data": {},
            "file_path": f["path"],
            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        invoice_registry.insert(0, new_item)
        background_tasks.add_task(run_extraction_worker, doc_id, f["path"], f["filename"])
    return {"status": "success", "count": len(files)}

@app.get("/api/export/excel")
async def export_excel():
    path = excel_gen.export_to_excel(invoice_registry)
    if not path:
        raise HTTPException(status_code=400, detail="No data to export")
    # Return path relative to the server root
    return {"file_url": path.replace('\\', '/')}

@app.get("/api/export/zip")
async def export_zip():
    if not invoice_registry:
        raise HTTPException(status_code=400, detail="Registry empty")
    
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for inv in invoice_registry:
            file_path = inv.get("file_path")
            if file_path and os.path.exists(file_path):
                zip_file.write(file_path, arcname=inv["filename"])
    
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer, 
        media_type="application/x-zip-compressed", 
        headers={"Content-Disposition": f"attachment; filename=Infinx_Bundle_{datetime.now().strftime('%H%M%S')}.zip"}
    )

@app.get("/api/export/xml/{invoice_id}")
async def export_xml(invoice_id: str):
    inv = next((i for i in invoice_registry if i["id"] == invoice_id), None)
    if not inv: 
        raise HTTPException(status_code=404, detail="Not found")
    xml_str = tally_gen.generate_purchase_xml(inv['raw_data'])
    return {"xml": xml_str}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
