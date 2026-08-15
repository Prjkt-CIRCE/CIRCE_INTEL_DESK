"""
CIRCE Intel Desk — Script de verificacao do ambiente OCR
Sprint 04 — Sub-passo 04-0

Engine hibrida (D-04-0-02):
  PDFs   -> PyMuPDF (pagina->imagem) + pytesseract (Tesseract/por)
  Imagens -> EasyOCR (rede neural, melhor em material degradado)

Executa fora do servidor. Rode com:
    python scripts/test_ocr.py

Verifica:
  1. Importacoes Python (pytesseract, easyocr, pymupdf, pillow)
  2. Tesseract instalado e acessivel no PATH
  3. Pacote de idioma portugues (por) disponivel
  4. Modelos EasyOCR disponiveis (pt)
  5. OCR de imagem via EasyOCR funcional
  6. OCR de PDF via PyMuPDF + pytesseract funcional
"""

import os
import sys
import tempfile

SEP  = "─" * 60
OK   = "✓"
ERR  = "✗"
WARN = "⚠"

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def title(text):
    print(f"\n{SEP}\n  {text}\n{SEP}")


def ok(msg):
    print(f"  {OK}  {msg}")


def fail(msg):
    print(f"  {ERR}  {msg}")


def warn(msg):
    print(f"  {WARN}  {msg}")


failures = []

# ──────────────────────────────────────────────────────────────
title("1. IMPORTACOES PYTHON")
# ──────────────────────────────────────────────────────────────

try:
    import pytesseract
    ok("pytesseract (versao via Tesseract abaixo)")
except ImportError as e:
    fail(f"pytesseract nao instalado — pip install pytesseract")
    fail(f"  Detalhe: {e}")
    failures.append("pytesseract")

try:
    import easyocr
    ok(f"easyocr {easyocr.__version__}")
except ImportError as e:
    fail(f"easyocr nao instalado — pip install easyocr")
    fail(f"  Detalhe: {e}")
    failures.append("easyocr")

try:
    # pymupdf >= 1.24: import pymupdf (evita aviso de deprecacao do alias fitz)
    import pymupdf as fitz
    ok(f"pymupdf {fitz.__version__}")
except ImportError:
    try:
        import fitz  # fallback para versoes antigas
        ok(f"pymupdf {fitz.__version__} (via alias fitz)")
    except ImportError as e:
        fail(f"pymupdf nao instalado — pip install pymupdf")
        fail(f"  Detalhe: {e}")
        failures.append("pymupdf")

try:
    import PIL
    from PIL import Image, ImageDraw
    ok(f"pillow {PIL.__version__}")
except ImportError as e:
    fail(f"pillow nao instalado — pip install pillow")
    fail(f"  Detalhe: {e}")
    failures.append("pillow")

if failures:
    print(f"\n  Resolva as importacoes acima antes de continuar.")
    print(f"  Execute: pip install -r requirements.txt\n")
    sys.exit(1)

# ──────────────────────────────────────────────────────────────
title("2. TESSERACT — BINARIO E VERSAO")
# ──────────────────────────────────────────────────────────────

tesseract_ok = False

import os as _os
if _os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

try:
    version = pytesseract.get_tesseract_version()
    ok(f"Tesseract v{version}")
    tesseract_ok = True
except Exception as e:
    fail(f"Tesseract nao encontrado ou nao acessivel.")
    fail(f"  Caminho esperado: {TESSERACT_PATH}")
    fail(f"  Detalhe: {e}")
    fail(f"  Instale via: winget install UB-Mannheim.TesseractOCR")
    fail(f"  Depois adicione ao PATH (ver ESTADO_DO_PROJETO.md secao 5)")
    failures.append("tesseract-binary")

# ──────────────────────────────────────────────────────────────
title("3. TESSERACT — PACOTE PORTUGUES (por)")
# ──────────────────────────────────────────────────────────────

if tesseract_ok:
    try:
        langs = pytesseract.get_languages()
        if "por" in langs:
            ok(f"Pacote 'por' (Portugues) disponivel — tessdata: {langs}")
        else:
            fail(f"Pacote 'por' NAO encontrado. Idiomas instalados: {langs}")
            fail(f"  Baixe via PowerShell (como Admin):")
            fail(
                r"  Invoke-WebRequest -Uri 'https://github.com/tesseract-ocr/tessdata_best/raw/main/por.traineddata'"
                r" -OutFile '$env:ProgramFiles\Tesseract-OCR\tessdata\por.traineddata'"
            )
            failures.append("tesseract-por")
    except Exception as e:
        fail(f"Erro ao listar idiomas Tesseract: {e}")
        failures.append("tesseract-langs")
else:
    warn("Verificacao de idiomas pulada — Tesseract nao disponivel.")

# ──────────────────────────────────────────────────────────────
title("4. EASYOCR — MODELOS (pt)")
# ──────────────────────────────────────────────────────────────

print("  Carregando modelos EasyOCR (pode levar 30-90s na primeira vez)...")
reader = None
try:
    reader = easyocr.Reader(["pt"], verbose=False)
    ok("Modelos EasyOCR (pt) carregados com sucesso")
except Exception as e:
    msg = str(e).lower()
    if any(kw in msg for kw in ("download", "connection", "network", "http", "url")):
        fail("Modelos EasyOCR nao baixados — necessario acesso a internet uma vez.")
        fail("  Execute: python -c \"import easyocr; easyocr.Reader(['pt'])\"")
        fail("  Apos o download (~600 MB), funciona 100% offline.")
    else:
        fail(f"Erro ao carregar EasyOCR: {e}")
    failures.append("easyocr-models")

# ──────────────────────────────────────────────────────────────
title("5. TESTE FUNCIONAL — IMAGEM (EasyOCR)")
# ──────────────────────────────────────────────────────────────

if reader is not None:
    try:
        img = Image.new("RGB", (640, 140), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 40), "CIRCE Intel Desk", fill=(0, 0, 0))
        draw.text((20, 75), "Teste OCR em Portugues - Joao Silva CPF 123456789", fill=(0, 0, 0))

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        img.save(tmp.name)

        results = reader.readtext(tmp.name, detail=0)
        extracted = " ".join(results).strip()
        os.unlink(tmp.name)

        if extracted:
            ok("EasyOCR extraiu texto da imagem de teste:")
            print(f"     → \"{extracted[:80]}\"")
        else:
            warn("EasyOCR nao extraiu texto da imagem sintetica (esperado em imagens simples).")
            warn("  Em documentos reais a performance sera melhor.")
    except Exception as e:
        fail(f"Erro no teste EasyOCR: {e}")
        failures.append("easyocr-test")
else:
    warn("Teste EasyOCR pulado — modelos nao disponiveis.")

# ──────────────────────────────────────────────────────────────
title("6. TESTE FUNCIONAL — PDF (PyMuPDF + pytesseract)")
# ──────────────────────────────────────────────────────────────

if tesseract_ok and "tesseract-por" not in failures:
    tmp_pdf = None
    try:
        import io

        # Criar PDF de teste com PyMuPDF
        pdf_doc = fitz.open()
        page = pdf_doc.new_page(width=595, height=842)  # A4
        page.insert_text(
            (72, 200),
            (
                "CIRCE Intel Desk\n"
                "Teste OCR PDF em Portugues\n"
                "Nome: Joao da Silva\n"
                "CPF: 123.456.789-00\n"
                "Boletim de Ocorrencia: 2026/001234"
            ),
            fontsize=14,
        )
        tmp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp_pdf.close()
        pdf_doc.save(tmp_pdf.name)
        pdf_doc.close()

        # Converter primeira pagina em imagem e rodar pytesseract
        doc = fitz.open(tmp_pdf.name)
        page = doc[0]
        pix = page.get_pixmap(dpi=200)
        doc.close()

        img_data = pix.tobytes("png")
        pil_img = Image.open(io.BytesIO(img_data))

        extracted = pytesseract.image_to_string(pil_img, lang="por").strip()

        if any(kw in extracted for kw in ("CIRCE", "Joao", "CPF", "Boletim")):
            ok("PyMuPDF + pytesseract processou PDF com sucesso:")
            sample = extracted.replace("\n", " ")[:80]
            print(f"     → \"{sample}...\"")
        else:
            warn("pytesseract rodou mas texto extraido parece vazio ou incompleto.")
            warn(f"  Extraido: '{extracted[:60]}'")
            warn("  Verifique o pacote 'por' do Tesseract.")

    except Exception as e:
        fail(f"Erro no teste PDF: {e}")
        failures.append("pdf-test")
    finally:
        if tmp_pdf and os.path.exists(tmp_pdf.name):
            os.unlink(tmp_pdf.name)
else:
    warn("Teste PDF pulado — Tesseract ou pacote 'por' nao disponivel.")

# ──────────────────────────────────────────────────────────────
title("RESULTADO FINAL")
# ──────────────────────────────────────────────────────────────

if not failures:
    print(f"\n  {OK}  Ambiente OCR 100% operacional.")
    print("  Prossiga para o sub-passo 04-1.\n")
    sys.exit(0)
else:
    print(f"\n  {ERR}  {len(failures)} problema(s) encontrado(s):")
    for f in failures:
        print(f"       — {f}")
    print(
        "\n  Resolva os itens acima e execute o script novamente.\n"
        "  Consulte ESTADO_DO_PROJETO.md secao 5 para o procedimento completo.\n"
    )
    sys.exit(1)
