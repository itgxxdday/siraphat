import cv2
import numpy as np
import os
import base64
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import tempfile 

# --- Flask Configuration ---
app = Flask(__name__)
# อนุญาตเฉพาะนามสกุลไฟล์ภาพ
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# ตรวจสอบนามสกุลไฟล์
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Core Analysis Function (UPDATED: Multi-color Droplet Detection & High Sensitivity with *10 Factor) ---
def analyze_droplets_core(img, paper_width, paper_height):
    """
    ฟังก์ชันหลักสำหรับการวิเคราะห์ภาพหยดละออง 
    (ใช้ Adaptive Thresholding และปรับค่าความหนาแน่นให้คูณ 10)
    """
    # ... ขั้นตอน 1-3 เหมือนเดิม (CLAHE, Adaptive Thresholding, Morphological Operations) ...
    # 1. ปรับ contrast ด้วย CLAHE
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8,8)) 
    cl = clahe.apply(l)
    lab = cv2.merge((cl, a, b))
    img_enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    # 2. การแปลงเป็น Grayscale และ Adaptive Thresholding
    gray = cv2.cvtColor(img_enhanced, cv2.COLOR_BGR2GRAY)
    block_size = 21 
    C = 5 
    mask = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                 cv2.THRESH_BINARY_INV, block_size, C)
    
    # 3. ทำความสะอาด mask (Morphological Operations)
    kernel_small = np.ones((3,3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_small, iterations=1) 
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_small, iterations=2)
    
    # 4. หาขอบ, กรองรูปร่าง, และนับจำนวนจุด (Contour Detection & Filtering)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # --- ตัวแปรสำหรับ Calibration ---
    paper_width_cm = paper_width if paper_width > 0 else 1
    paper_height_cm = paper_height if paper_height > 0 else 1
    paper_area_real = paper_width_cm * paper_height_cm
    paper_area_pixels = img.shape[0] * img.shape[1]
    
    # อัตราส่วน: cm² ต่อ pixel
    pixel_to_real_ratio_area = paper_area_real / paper_area_pixels if paper_area_pixels > 0 else 0 
    # อัตราส่วน: cm ต่อ pixel
    pixel_to_real_ratio_linear = np.sqrt(pixel_to_real_ratio_area)

    # --- เกณฑ์การคัดกรอง ---
    min_area_threshold = 10 
    min_circularity = 0.5 # หยดควรมีความกลมในระดับหนึ่ง (1.0 = กลมสมบูรณ์)
    
    valid_contours = []
    diameters_pixels = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area_threshold:
            continue
        
        # ก. การกรองรูปร่าง (Circularity)
        perimeter = cv2.arcLength(cnt, True)
        if perimeter == 0:
            continue
            
        # Circularity = 4*pi*Area / Perimeter^2 (1.0 คือวงกลมสมบูรณ์)
        circularity = 4 * np.pi * area / (perimeter * perimeter)
        if circularity < min_circularity:
            continue
            
        # ข. การวัดขนาด
        # ใช้ Bounding Circle ที่เล็กที่สุด
        (x, y), radius = cv2.minEnclosingCircle(cnt)
        diameter_pixels = 2 * radius
        
        diameters_pixels.append(diameter_pixels)
        valid_contours.append(cnt)
    
    count = len(valid_contours)
    
    # 5. คำนวณขนาดเฉลี่ย
    mean_diameter_pixels = np.mean(diameters_pixels) if count > 0 else 0
    # แปลงจาก pixels เป็น micrometers (µm) - ค่าทั่วไปใช้หน่วยนี้
    # 1 cm = 10,000 µm
    mean_diameter_um = mean_diameter_pixels * pixel_to_real_ratio_linear * 10000 
    
    # 6. วาดขอบและหมายเลขบนภาพ
    output = img.copy()
    cv2.drawContours(output, valid_contours, -1, (0, 0, 255), 2) 
    for i, cnt in enumerate(valid_contours):
        x, y, w, h = cv2.boundingRect(cnt)
        cx = x + w//2
        cy = y + h//2
        cv2.putText(output, str(i+1), (cx-10, cy), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 0, 0), 2, cv2.LINE_AA) 
    
    text = f"Droplets detected: {count} | Avg Dia: {mean_diameter_um:.0f} µm"
    cv2.putText(output, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 100, 255), 2, cv2.LINE_AA)

    # 7. คำนวณพื้นที่และวิเคราะห์ความหนาแน่น
    paper_area_real = paper_width_cm * paper_height_cm
    drop_area_pixels = np.sum(mask > 0) 
    drop_area_real = drop_area_pixels * pixel_to_real_ratio_area
    
    if paper_area_real > 0:
        percent_coverage = (drop_area_real / paper_area_real) * 100
        # ใช้การหาร 10 ตามคำขอครั้งล่าสุด (เพื่อแสดงผล)
        droplets_per_sq_cm = (count / paper_area_real) / 10.0
    else:
        percent_coverage = 0.0
        droplets_per_sq_cm = 0.0

    # 8. แปลผลตามเกณฑ์ใหม่ (*** เกณฑ์อิงจาก Count และ Size ***)
    # เกณฑ์ทั่วไปสำหรับขนาดหยด: 
    # 50-100 µm: Fine (ป้องกันแมลง)
    # 100-300 µm: Medium (ป้องกันวัชพืช/โรคพืชทั่วไป)
    # 300+ µm: Coarse (ยากต่อการปกคลุม)

    if count > 50 and 100 <= mean_diameter_um <= 300:
        efficacy_result = "ยอดเยี่ยม: จำนวนมากและขนาดเหมาะสมสำหรับการป้องกันโรคพืชและแมลง"
    elif count >= 30 and 50 <= mean_diameter_um <= 350:
        efficacy_result = "ดี: จำนวนพอใช้ แต่ขนาดอาจไม่เหมาะสมที่สุด (อาจเล็ก/ใหญ่ไป)"
    elif count >= 20 and mean_diameter_um > 50:
        efficacy_result = "พอใช้: จำนวนต่ำหรือขนาดไม่เหมาะสม ต้องปรับปรุงการพ่น"
    else:
        efficacy_result = "ต้องปรับปรุง: ประสิทธิภาพต่ำสำหรับการป้องกันทุกชนิด"
    
    # ฟังก์ชันช่วยแปลงภาพ OpenCV เป็น Base64 string
    def cv2_to_base64(img_cv):
        is_success, buffer = cv2.imencode(".jpeg", img_cv, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return base64.b64encode(buffer).decode("utf-8")
    
    original_img_base64 = cv2_to_base64(img)
    output_img_base64 = cv2_to_base64(output)

    # 9. เตรียมผลลัพธ์
    results = {
        "count": count,
        "mean_diameter_um": f"{mean_diameter_um:.0f} µm", # <-- เพิ่มผลลัพธ์ใหม่
        "paper_area_real": f"{paper_area_real:.2f} cm²",
        "drop_area_real": f"{drop_area_real:.2f} cm²",
        "percent_coverage": f"{percent_coverage:.2f}%",
        "droplets_per_sq_cm": f"{droplets_per_sq_cm:.2f} หยด/cm²",
        "efficacy_result": efficacy_result 
    }

    return results, original_img_base64, output_img_base64

# --- อัปเดตการใช้งาน Flask Route ---
# คุณต้องเปลี่ยนฟังก์ชันที่ถูกเรียกใน route '/analyze' จาก 'analyze_droplets_core' 
# เป็น 'analyze_droplets_core_improved'

@app.route('/analyze', methods=['POST'])
def analyze():
    # ... (ส่วนรับค่าจากฟอร์มเหมือนเดิม) ...
    try:
        paper_width = float(request.form.get('paper_width'))
        paper_height = float(request.form.get('paper_height'))
    except (ValueError, TypeError):
        return jsonify({"error": "ค่าความกว้างและความยาวไม่ถูกต้อง"}), 400

    if 'file' not in request.files:
        return jsonify({"error": "ไม่พบไฟล์ในคำขอ"}), 400
    
    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "ไม่ได้เลือกไฟล์"}), 400

    if file and allowed_file(file.filename):
        # 2. อ่านไฟล์เข้าสู่หน่วยความจำ
        file_bytes = file.read()
        np_arr = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
             return jsonify({"error": "ไม่สามารถอ่านไฟล์ภาพได้ โปรดตรวจสอบรูปแบบไฟล์"}), 400
        
        # 3. รันการวิเคราะห์ด้วยฟังก์ชันที่ปรับปรุงแล้ว
        results, original_img_b64, output_img_b64 = analyze_droplets_core_improved(img, paper_width, paper_height) # <--- เปลี่ยนตรงนี้!

        if "error" in results:
             return jsonify(results), 500

        # 4. ส่งผลลัพธ์กลับไปให้ JavaScript
        return jsonify({
            "success": True,
            "results": results,
            "original_image": f"data:image/jpeg;base64,{original_img_b64}",
            "output_image": f"data:image/jpeg;base64,{output_img_b64}"
        })

    return jsonify({"error": "นามสกุลไฟล์ไม่ได้รับอนุญาต (ใช้ได้เฉพาะ png, jpg, jpeg)"}), 400
