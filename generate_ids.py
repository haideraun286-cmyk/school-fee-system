import os
import django
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schoolsystem.settings')
django.setup()

from students.models import Student

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_PATH = os.path.join(BASE_DIR, 'static', 'template.png')
os.makedirs(os.path.join(BASE_DIR, 'id_cards'), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, 'barcodes'), exist_ok=True)

# ── Template dimensions (measured from your PNG) ───────────────
# 1011 x 639 px
DPI = 300
MM  = DPI / 25.4

def px(mm_val):
    return round(mm_val * MM)

# ── ALL coordinates in one dictionary ─────────────────────────
COORDS = {
    'name':    (px(41.8), px(15.8)),   # inside name box
    'id':      (px(39.8), px(20.1)),   # after "ID:" label
    'class':   (px(39.8), px(23.1)),   # after "Class:" label
    'dob':     (px(47.5), px(26.2)),   # after "Date of Birth:" label
    'address': (px(42.6), px(29.4)),   # after "Address:" label
    'photo':   (px(7.2),  px(16.3), px(21.2), px(20.3)),  # x, y, w, h
    'barcode': (px(5.8),  px(38.0), px(24.0), px(8.0)),   # x, y, w, h
}

# ── Fonts ──────────────────────────────────────────────────────
try:
    FONT_REG  = ImageFont.truetype("arial.ttf",   px(2.6))
    FONT_BOLD = ImageFont.truetype("arialbd.ttf", px(2.6))
except Exception:
    FONT_REG  = ImageFont.load_default()
    FONT_BOLD = FONT_REG

# ── Barcode generator ──────────────────────────────────────────
def make_barcode(student_id):
    out = os.path.join(BASE_DIR, 'barcodes', student_id)
    code = barcode.get('code128', student_id, writer=ImageWriter())
    code.save(out, options={
        'write_text':    True,
        'font_size':     6,
        'text_distance': 2,
        'module_height': 8,
        'quiet_zone':    2,
    })
    return out + '.png'

# ── Main ───────────────────────────────────────────────────────
def generate_card(student):
    # 1. Open template — never redraw it
    card = Image.open(TEMPLATE_PATH).convert('RGBA')
    draw = ImageDraw.Draw(card)

    # 2. Paste student photo
    x, y, w, h = COORDS['photo']
    if student.photo:
        photo_path = os.path.join(BASE_DIR, 'media', str(student.photo))
        if os.path.exists(photo_path):
            photo = Image.open(photo_path).convert('RGB').resize((w, h), Image.LANCZOS)
            card.paste(photo, (x, y))

    # 3. Paste barcode
    bc_path = make_barcode(student.student_id)
    bx, by, bw, bh = COORDS['barcode']
    bc_img = Image.open(bc_path).convert('RGB').resize((bw, bh), Image.LANCZOS)
    card.paste(bc_img, (bx, by))

    # 4. Draw ONLY dynamic text values
    BLACK = (0, 0, 0)

    draw.text(COORDS['name'],    student.name,          font=FONT_BOLD, fill=BLACK)
    draw.text(COORDS['id'],      student.student_id,    font=FONT_REG,  fill=BLACK)
    draw.text(COORDS['class'],   f"{student.class_name} - {student.section}", font=FONT_REG, fill=BLACK)
    draw.text(COORDS['dob'],     str(student.date_of_birth) if student.date_of_birth else "—", font=FONT_REG, fill=BLACK)
    draw.text(COORDS['address'], student.address[:35] if student.address else "—", font=FONT_REG, fill=BLACK)

    # 5. Save
    out_path = os.path.join(BASE_DIR, 'id_cards', f'{student.student_id}.png')
    card.convert('RGB').save(out_path, dpi=(DPI, DPI))
    print(f"Done: {student.name}")

if __name__ == '__main__':
    # Save your template PNG as static/template.png first
    students = list(Student.objects.all())
    for s in students:
        generate_card(s)
    print(f"\n{len(students)} cards generated in /id_cards/")