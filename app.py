import cv2
import numpy as np
import os
import base64
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import tempfile # นำเข้า tempfile เพื่อจัดการไฟล์ชั่วคราว

# --- Flask Configuration ---
app = Flask(__name__)
# อนุญาตเฉพาะนามสกุลไฟล์ภาพ
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# ตรวจสอบนามสกุลไฟล์
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Core Analysis Function (UPDATED: Multi-color Droplet Detection) ---
def analyze_droplets_core(img, paper_width, paper_height):
    """
    ฟังก์ชันหลักสำหรับการวิเคราะห์ภาพหยดละออง (ปรับปรุงเพื่อตรวจจับหลายสี)
    """
    
    # 1. ปรับ contrast ด้วย CLAHE (ยังคงช่วยปรับปรุงคุณภาพภาพ)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    lab = cv2.merge((cl, a, b))
    img_enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    # 2. การแปลงเป็น Grayscale และ Adaptive Thresholding เพื่อตรวจจับ 'สิ่งที่ไม่ใช่สีขาว'
    # แปลงเป็น Grayscale
    gray = cv2.cvtColor(img_enhanced, cv2.COLOR_BGR2GRAY)
    
    # ใช้ Adaptive Thresholding เพื่อจัดการกับแสงที่ไม่สม่ำเสมอ
    block_size = 31 # ต้องเป็นเลขคี่ที่ใหญ่กว่า 1
    C = 10 # ค่าคงที่ที่ถูกลบออกจากค่าเฉลี่ย
    # THRESH_BINARY_INV: ทำให้สิ่งที่มืดกว่า (หยดละออง) กลายเป็นสีขาว (255) และพื้นหลังสว่างกลายเป็นสีดำ (0)
    mask = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                 cv2.THRESH_BINARY_INV, block_size, C)
    
    # 3. ทำความสะอาด mask (Morphological Operations)
    kernel = np.ones((3,3), np.uint8)
    # Open: ลบจุดรบกวน (Noise) ขนาดเล็ก
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    # Close: เชื่อมต่อหยดละอองที่อยู่ใกล้กันเล็กน้อยให้เป็น Contour เดียวกัน
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    # 4. หาขอบและนับจำนวนจุด (Contour Detection)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # กรอง Contours ที่เล็กเกินไป (Noise)
    min_area_threshold = 50 # ปรับค่านี้ตามความเหมาะสม
    valid_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area_threshold]
    count = len(valid_contours)

    # 5. วาดขอบและหมายเลขบนภาพ
    output = img.copy()
    cv2.drawContours(output, valid_contours, -1, (0, 0, 255), 2) # วาดเส้นขอบสีแดง
    for i, cnt in enumerate(valid_contours):
        x, y, w, h = cv2.boundingRect(cnt)
        cx = x + w//2
        cy = y + h//2
        # วาดหมายเลขสีฟ้า
        cv2.putText(output, str(i+1), (cx-10, cy), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 0, 0), 2, cv2.LINE_AA) 
    
    text = f"Droplets detected: {count}"
    cv2.putText(output, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 100, 255), 3, cv2.LINE_AA)

    # 6. คำนวณพื้นที่และวิเคราะห์ความหนาแน่น
    paper_area_real = paper_width * paper_height
    paper_area_pixels = img.shape[0] * img.shape[1]
    
    if paper_area_pixels == 0:
        return {"error": "ไม่สามารถคำนวณพื้นที่พิกเซลได้"}, None, None

    pixel_to_real_ratio = paper_area_real / paper_area_pixels
    # คำนวณพื้นที่ของหยดละอองจาก mask ที่ทำ Adaptive Thresholding
    drop_area_pixels = np.sum(mask > 0) 
    drop_area_real = drop_area_pixels * pixel_to_real_ratio
    
    if paper_area_real > 0:
        percent_coverage = (drop_area_real / paper_area_real) * 100
        droplets_per_sq_cm = count / paper_area_real
    else:
        percent_coverage = 0.0
        droplets_per_sq_cm = 0.0

    # แปลผลตามเกณฑ์
    if droplets_per_sq_cm > 50:
        efficacy_result = "ยอดเยี่ยม: ป้องกันได้ทั้งโรคพืช, วัชพืช, และแมลงศัตรูพืช"
    elif droplets_per_sq_cm >= 30:
        efficacy_