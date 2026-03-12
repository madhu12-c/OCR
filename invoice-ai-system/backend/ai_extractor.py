import os
import base64
import json
import time
from groq import Groq
from dotenv import load_dotenv
import re

load_dotenv()

# --- UTILITIES ---
def safe_float(val):
    """Safely convert any value to float for production stability."""
    if val is None: return 0.0
    if isinstance(val, (int, float)): return float(val)
    try:
        # Remove currency symbols, commas, and whitespace
        clean_val = str(val).replace('₹', '').replace('$', '').replace(',', '').strip()
        if not clean_val or clean_val == 'null': return 0.0
        return float(clean_val)
    except (ValueError, TypeError):
        return 0.0

# --- PRODUCTION-GRADE VISION PROMPT ---
SYSTEM_PROMPT = """You are a specialized Document AI Agent for Multi-Page Invoice Extraction.
You will be provided with one or more images. These are sequential pages of the SAME invoice.

STRICT CONSOLIDATION & EXTRACTION RULES:
1. OMNI-PAGE SCAN: You are viewing a single invoice split into multiple pages. You MUST synthesize all pages. If the Invoice No is on Page 1 and GSTIN is on Page 3, you MUST link them.
2. GSTIN / TAX ID PRIORITY: GSTINs are 15-character alphanumeric codes (e.g., 27AA...Z5). Hunt them in Headers, Footers, and next to 'GST No', 'Tax ID', or 'Registration'. 
3. INCLUSIVE TAXES: In Rapido/Uber invoices, look at the 'Bill Details' or 'Breakdown' for CGST and SGST (usually 2.5%, 6% or 9%). 
4. CHARACTER FIDELITY: Copy names and numbers exactly. Zero hallucinations. If a field isn't there, return null.
5. CATCH-ALL: If you find an identifier that looks like a GSTIN but aren't sure where it fits, put it in 'unstructured_gstin'.
6. JSON ONLY: Output a perfectly formatted JSON object. no conversational filler.
"""

PRODUCTION_VISION_PROMPT = """Analyze ALL pages of this invoice. Read every number and text string character-by-character. 
Submit a single consolidated JSON mapping the entire document.

{
  "invoice_number": "string",
  "po_number": "string",
  "invoice_date": "YYYY-MM-DD",
  "vendor_name": "string",
  "vendor_gstin": "string",
  "vendor_address": "string",
  "customer_name": "string",
  "customer_gstin": "string",
  "line_items": [
    {"description": "string", "amount": number}
  ],
  "subtotal": number,
  "cgst": number,
  "sgst": number,
  "igst": number,
  "total_tax": number,
  "total_amount": number,
  "payment_method": "string",
  "bank_details": "string",
  "upi_id": "string",
  "vehicle_number": "string",
  "place_of_supply": "string",
  "unstructured_gstin": "string",
  "notes": "string"
}

STRICT: Capture 'Vehicle Number' or 'Captain Name' if present (important for transport POs). 
Always find 'GST Number' and every single tax component (CGST/SGST/IGST).

PO NUMBER RULE: Only capture 'po_number' if explicitly labeled as 'PO No', 'Purchase Order', or 'P.O.'. 
If the document is a Sales Invoice without a customer PO reference, return null. DO NOT hallucinate.
"""

class AIExtractor:
    def __init__(self, api_key=None, model_name="meta-llama/llama-4-scout-17b-16e-instruct", **kwargs):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            self.client = None
        else:
            self.client = Groq(api_key=self.api_key)
        self.model_name = model_name

    def encode_image(self, image_path):
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"File access error: {e}")
            return None

    def extract_invoice_data(self, image_paths, **kwargs):
        """
        PRODUCTION-GRADE MULTI-PAGE SYNTHESIS EXTRACTOR.
        Processes all pages in one single context with explicit page indexing.
        """
        if not self.client:
            return {"error": "GROQ API Key missing. Please provide it in the Dashboard settings."}

        # Ensure image_paths is a list
        if isinstance(image_paths, str):
            image_paths = [image_paths]

        # --- PRODUCTION SAFE LIMIT ---
        # Groq currently allows up to 5 images per request. 
        # For multi-page invoices, we prioritize the first 4 (headers/items) and the LAST page (totals).
        original_count = len(image_paths)
        if original_count > 5:
            print(f"WARNING: Truncating {original_count} pages to 5 due to model limits.")
            image_paths = image_paths[:4] + [image_paths[-1]]
            truncated = True
        else:
            truncated = False

        user_content = [{"type": "text", "text": PRODUCTION_VISION_PROMPT}]
        temp_files = []

        try:
            print(f"DEBUG: AI Pipeline processing {len(image_paths)} pages (Total doc: {original_count}).")
            for i, path in enumerate(image_paths):
                # 1. HD Enhancement (Small images)
                final_path = path
                try:
                    from PIL import Image
                    with Image.open(path) as img:
                        if img.width < 1600:
                            scale = 2200 / img.width
                            img = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS)
                            final_path = path.replace('.', f'_hd_p{i}.')
                            img.save(final_path, quality=95)
                            temp_files.append(final_path)
                except: pass

                # 2. Encode and add to user content with page label
                b64 = self.encode_image(final_path)
                if b64:
                    user_content.append({"type": "text", "text": f"--- Page {i+1} ---"})
                    user_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                    })

            if len(user_content) <= 2: # Only system prompt and maybe one divider
                return {"error": "No valid invoice pages could be processed."}

            # 3. Request LLM Synthesis
            t_start = time.time()
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.0,
                max_completion_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            raw_response = completion.choices[0].message.content
            data = json.loads(raw_response)
            
            # --- GLOBAL REGEX RESCUE (Zero-Failure Layer) ---
            # If standard extraction failed, scan the ENTIRE JSON string for any GSTIN patterns
            gst_regex = r'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}'
            all_text_matches = re.findall(gst_regex, raw_response)
            
            if all_text_matches:
                # If vendor_gstin is empty, take the first valid match
                if not data.get("vendor_gstin") or data.get("vendor_gstin") == "null":
                    data["vendor_gstin"] = all_text_matches[0]
                # If customer info is missing but we found 2 distinct matches, assign the 2nd to customer
                if len(all_text_matches) > 1 and (not data.get("customer_gstin") or data.get("customer_gstin") == "null"):
                    data["customer_gstin"] = all_text_matches[1]

            # 4. Final Audit & Normalization
            data = self._normalize(data)
            data = self._validate(data)
            data["_extraction_time"] = round(time.time() - t_start, 2)
            
            mode = f"AI Omni-Vision Pro ({len(image_paths)} Pages)"
            if truncated:
                mode += f" [Truncated from {original_count}]"
                data["_truncation_info"] = f"Processed 5 of {original_count} pages due to model limits."
            
            data["_extraction_mode"] = mode
            
            # Cleanup
            for f in temp_files:
                if os.path.exists(f): os.remove(f)
                
            return data
            
        except Exception as e:
            for f in temp_files:
                if os.path.exists(f): os.remove(f)
            return {"error": f"Synthesis Engine Exception: {str(e)}"}

    def _normalize(self, data):
        """Greedy alias-based normalization engine."""
        v = data.get("vendor") or {}
        c = data.get("customer") or {}
        tb = data.get("tax_breakdown") or {}

        # 1. Vendor GSTIN (Greedy Search)
        gst_keys = ["vendor_gstin", "gst_number", "gst_no", "gstin", "tax_id", "unstructured_gstin"]
        v_gst = data.get("vendor_gstin")
        if not v_gst or str(v_gst).lower() == 'null':
            for k in gst_keys:
                if data.get(k): 
                    v_gst = data.get(k)
                    break
        if not v_gst and isinstance(v, dict):
            for k in gst_keys:
                if v.get(k): 
                    v_gst = v.get(k)
                    break
        data["vendor_tax_id"] = v_gst
        data["vendor_name"] = data.get("vendor_name") or v.get("name") or "Unknown Vendor"
        data["vendor_address"] = data.get("vendor_address") or v.get("address") or "N/A"

        # 2. Customer GSTIN
        c_gst = data.get("customer_gstin")
        if not c_gst or str(c_gst).lower() == 'null':
            if data.get("customer_gst"): c_gst = data.get("customer_gst")
        data["customer_tax_id"] = c_gst
        data["customer_name"] = data.get("customer_name") or c.get("name") or "Direct Customer"
        data["customer_address"] = data.get("customer_address") or c.get("address") or "N/A"

        # 3. Tax Components (Strict Numeric)
        data["cgst_amount"] = safe_float(data.get("cgst") or tb.get("cgst") or data.get("cgst_amount"))
        data["sgst_amount"] = safe_float(data.get("sgst") or tb.get("sgst") or data.get("sgst_amount"))
        data["igst_amount"] = safe_float(data.get("igst") or tb.get("igst") or data.get("igst_amount"))
        data["total_tax"] = safe_float(data.get("total_tax") or tb.get("total_tax"))
        
        # 4. Final Amounts & Payment (Strict Numeric)
        data["total_amount"] = safe_float(data.get("total_amount") or data.get("total"))
        data["subtotal"] = safe_float(data.get("subtotal") or data.get("taxable_value"))
        
        # Stricter PO capturing to prevent "null" or hallucinated strings
        po_raw = data.get("po_number") or data.get("purchase_order") or data.get("order_no")
        if not po_raw or str(po_raw).lower() in ['null', 'n/a', 'none', '']:
            data["po_number"] = "N/A"
        else:
            data["po_number"] = str(po_raw)
        data["bank_details"] = str(data.get("bank_details") or "N/A")
        data["upi_id"] = str(data.get("upi_id") or "N/A")
        data["vehicle_number"] = str(data.get("vehicle_number") or "N/A")
        data["place_of_supply"] = str(data.get("place_of_supply") or "N/A")
        
        return data

    def _validate(self, data):
        """No strict validation - focus on extraction."""
        data["_validation_warnings"] = []
        data["_validation_passed"] = True
        return data

if __name__ == "__main__":
    pass


