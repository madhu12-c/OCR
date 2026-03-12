import os
import shutil

class LocalScanner:
    def __init__(self, watch_dir="data/local_import"):
        self.watch_dir = watch_dir
        self.upload_dir = "data/uploads"
        os.makedirs(self.watch_dir, exist_ok=True)
        os.makedirs(self.upload_dir, exist_ok=True)

    def scan_and_move(self):
        """
        Scans the watch directory for new invoices and moves them to the upload directory.
        Returns a list of moved file paths.
        """
        moved_files = []
        for filename in os.listdir(self.watch_dir):
            if filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                src = os.path.join(self.watch_dir, filename)
                dest = os.path.join(self.upload_dir, filename)
                
                # If file already exists in dest, add a timestamp or skip
                if os.path.exists(dest):
                    basename, ext = os.path.splitext(filename)
                    import time
                    filename = f"{basename}_{int(time.time())}{ext}"
                    dest = os.path.join(self.upload_dir, filename)

                try:
                    shutil.move(src, dest)
                    moved_files.append({
                        "filename": filename,
                        "path": dest
                    })
                except Exception as e:
                    print(f"Error moving file {filename}: {e}")
        
        return moved_files

if __name__ == "__main__":
    # Test block
    scanner = LocalScanner()
    # files = scanner.scan_and_move()
    # print(f"Moved {len(files)} files.")
