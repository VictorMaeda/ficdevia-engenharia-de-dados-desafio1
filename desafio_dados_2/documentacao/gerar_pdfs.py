"""
Script para compilar a documentação Markdown em PDFs profissionais
atendendo aos entregáveis da pasta documentacao/ do Desafio 2:
- arquitetura.pdf
- linhagem.pdf
- storytelling.pdf
"""

import os
import subprocess
import markdown

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DOCS_DIR = os.path.dirname(os.path.abspath(__file__))

CSS_STYLE = """
@page {
    size: A4;
    margin: 20mm 15mm 20mm 15mm;
}
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #1a202c;
    background-color: #ffffff;
    line-height: 1.6;
    font-size: 10.5pt;
}
h1, h2, h3, h4 {
    color: #1a365d;
    font-weight: 700;
}
h1 {
    font-size: 20pt;
    border-bottom: 2px solid #2b6cb0;
    padding-bottom: 8px;
    margin-top: 0;
}
h2 {
    font-size: 14pt;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 5px;
    margin-top: 24px;
}
h3 {
    font-size: 12pt;
    margin-top: 18px;
}
p, ul, ol {
    margin-bottom: 12px;
}
code {
    background-color: #edf2f7;
    padding: 2px 5px;
    border-radius: 4px;
    font-family: "Cascadia Code", "Courier New", monospace;
    font-size: 9.5pt;
    color: #805ad5;
}
pre {
    background-color: #1a202c;
    color: #e2e8f0;
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;
    font-family: "Cascadia Code", "Courier New", monospace;
    font-size: 8.5pt;
    line-height: 1.4;
}
pre code {
    background-color: transparent;
    color: inherit;
    padding: 0;
}
blockquote {
    border-left: 4px solid #3182ce;
    margin: 14px 0;
    padding: 8px 16px;
    background-color: #ebf8ff;
    color: #2b6cb0;
    font-style: italic;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 9.5pt;
}
th, td {
    border: 1px solid #cbd5e0;
    padding: 8px 10px;
    text-align: left;
}
th {
    background-color: #edf2f7;
    color: #2d3748;
    font-weight: 600;
}
tr:nth-child(even) {
    background-color: #f7fafc;
}
hr {
    border: 0;
    height: 1px;
    background-color: #e2e8f0;
    margin: 20px 0;
}
.header-box {
    background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
    color: white;
    padding: 16px 20px;
    border-radius: 8px;
    margin-bottom: 24px;
}
.header-box h1 {
    color: white;
    border-bottom: none;
    margin: 0;
}
.badge {
    display: inline-block;
    padding: 3px 8px;
    background-color: #e2e8f0;
    border-radius: 12px;
    font-size: 8.5pt;
    font-weight: 600;
    color: #4a5568;
}
"""

def markdown_to_pdf(md_filename, pdf_filename):
    md_path = os.path.join(DOCS_DIR, md_filename)
    pdf_path = os.path.join(DOCS_DIR, pdf_filename)
    html_tmp = os.path.join(DOCS_DIR, f"_tmp_{os.path.splitext(md_filename)[0]}.html")

    if not os.path.exists(md_path):
        print(f"[-] Arquivo não encontrado: {md_path}")
        return False

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Converter markdown com tabelas e blocos de código
    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "nl2br", "toc"]
    )

    full_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <title>{os.path.splitext(md_filename)[0].upper()}</title>
    <style>{CSS_STYLE}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    with open(html_tmp, "w", encoding="utf-8") as f:
        f.write(full_html)

    file_url = "file:///" + html_tmp.replace("\\", "/")

    cmd = [
        CHROME_PATH,
        "--headless",
        "--no-sandbox",
        "--disable-gpu",
        f"--print-to-pdf={pdf_path}",
        file_url
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        if os.path.exists(pdf_path):
            size_kb = os.path.getsize(pdf_path) / 1024
            print(f"[+] Gerado com sucesso: {pdf_filename} ({size_kb:.1f} KB)")
            return True
    except Exception as e:
        print(f"[-] Erro ao compilar {pdf_filename}: {e}")
        return False
    finally:
        if os.path.exists(html_tmp):
            os.remove(html_tmp)

def main():
    print("=== Gerando PDFs da Documentação (Desafio 2) ===")
    targets = [
        ("arquitetura.md", "arquitetura.pdf"),
        ("linhagem.md", "linhagem.pdf"),
        ("storytelling.md", "storytelling.pdf"),
        ("dados_mestres.md", "dados_mestres.pdf"),
        ("rf31_qualidade.md", "qualidade.pdf"),
    ]

    for md_file, pdf_file in targets:
        markdown_to_pdf(md_file, pdf_file)

if __name__ == "__main__":
    main()
