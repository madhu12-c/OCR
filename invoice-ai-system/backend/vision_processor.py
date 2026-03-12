import os
import fitz  # PyMuPDF is a self-contained PDF engine, no Poppler needed
from PIL import Image

class VisionProcessor:
    def __init__(self):
        self.output_dir = "data/uploads"
        os.makedirs(self.output_dir, exist_ok=True)

    def prepare_file(self, file_path):
        """
        Converts PDF to Images (ALL PAGES) with robust path handling.
        Returns: list of image paths.
        """
        base_path, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        if ext == '.pdf':
            image_paths = []
            try:
                pdf_document = fitz.open(file_path)
                
                if pdf_document.page_count == 0:
                    print(f"Error: {file_path} is empty")
                    return []
                    
                zoom = 4.0
                mat = fitz.Matrix(zoom, zoom)
                
                for page_num in range(pdf_document.page_count):
                    page = pdf_document.load_page(page_num)
                    pix = page.get_pixmap(matrix=mat)
                    
                    # Robust naming: base_path + page suffix + extension
                    out_path = f"{base_path}_pg{page_num+1}.jpg"
                    pix.save(out_path)
                    image_paths.append(out_path)
                
                pdf_document.close()
                return image_paths
            except Exception as e:
                print(f"PDF Conversion Error: {e}")
                return []
        elif ext in ['.jpg', '.jpeg', '.png']:
            return [file_path]
        else:
            return []

if __name__ == "__main__":
    # Test block
    processor = VisionProcessor()
    # img = processor.prepare_file("test.pdf")
    # print(img)
