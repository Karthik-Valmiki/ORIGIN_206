import os
from fastapi import UploadFile, HTTPException
import shutil
from typing import List
import uuid

def save_upload(inspection_id: uuid.UUID, index: int, file: UploadFile, upload_dir: str = "uploads") -> str:
    target_dir = os.path.join(upload_dir, str(inspection_id))
    os.makedirs(target_dir, exist_ok=True)
    
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    filename = f"{index}_original.{ext}"
    file_path = os.path.join(target_dir, filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    return file_path

def get_file_path(inspection_id: str, filename: str, upload_dir: str = "uploads") -> str:
    path = os.path.join(upload_dir, str(inspection_id), filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return path
