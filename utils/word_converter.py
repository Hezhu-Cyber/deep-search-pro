"""Markdown → PDF 转换引擎。

优先使用跨平台的 WeasyPrint；若当前环境不可用（例如 Windows 未安装 Pango），
自动回退到 Microsoft Word COM（需要本机安装 Office）。两者都不可用时返回可读错误。
"""
import logging
from pathlib import Path

try:
    import markdown
except ImportError:  # pragma: no cover
    markdown = None

_PDF_CSS = """
body { font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
       font-size: 12pt; line-height: 1.7; margin: 32px; }
h1, h2, h3, h4 { color: #1f3864; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; }
th, td { border: 1px solid #666; padding: 6px 8px; }
pre { background-color: #f5f5f5; padding: 10px; border-radius: 4px; white-space: pre-wrap; }
code { font-family: Consolas, Monaco, monospace; }
img { max-width: 100%; }
"""


def _md_to_html(md_abs_path: Path) -> str:
    """把 Markdown 文件转换为带基础样式的 HTML 字符串。"""
    if markdown is None:
        raise RuntimeError("缺少依赖库 markdown，请先 pip install markdown")
    md_content = Path(md_abs_path).read_text(encoding="utf-8")
    html_body = markdown.markdown(
        md_content, extensions=["tables", "fenced_code", "codehilite", "toc"]
    )
    return (
        "<html><head><meta charset='UTF-8'>"
        f"<style>{_PDF_CSS}</style></head><body>{html_body}</body></html>"
    )


def convert_md_to_pdf_via_weasyprint(md_abs_path: Path, pdf_abs_path: Path) -> str:
    """WeasyPrint 引擎（跨平台，Linux / macOS / Docker 推荐）。"""
    from weasyprint import HTML  # 延迟导入：避免在缺少 pango 的环境导入即报错

    html = _md_to_html(md_abs_path)
    HTML(string=html, base_url=str(Path(md_abs_path).parent.resolve())).write_pdf(
        str(pdf_abs_path)
    )
    if Path(pdf_abs_path).exists():
        return f"成功转换: {pdf_abs_path} (WeasyPrint 引擎)"
    return f"转换完成但未生成文件: {pdf_abs_path}"


def convert_md_to_pdf_via_word(md_abs_path: Path, pdf_abs_path: Path) -> str:
    """Word COM 引擎（Windows + Office 环境，排版最接近本地 Office）。"""
    try:
        import pythoncom
        import win32com.client
    except ImportError:
        return "缺少依赖库，请安装: pip install pywin32（仅 Windows 需要）"

    temp_html_path = Path(md_abs_path).with_suffix(".temp.html")
    temp_html_path.write_text(_md_to_html(md_abs_path), encoding="utf-8")
    word_app = None
    try:
        pythoncom.CoInitialize()
        word_app = win32com.client.Dispatch("Word.Application")
        word_app.Visible = False
        word_app.DisplayAlerts = False
        doc = word_app.Documents.Open(str(temp_html_path.resolve()))
        doc.SaveAs(str(Path(pdf_abs_path).resolve()), FileFormat=17)  # wdFormatPDF = 17
        doc.Close(SaveChanges=0)
        if Path(pdf_abs_path).exists():
            return f"成功转换: {pdf_abs_path} (Word 引擎)"
        return f"转换完成但未生成文件: {pdf_abs_path}"
    except Exception as exc:  # noqa: BLE001
        logging.error(f"Word 转换 PDF 失败: {exc}", exc_info=True)
        return f"转换失败: {exc}"
    finally:
        if word_app:
            try:
                word_app.Quit()
            except Exception:
                pass
        temp_html_path.unlink(missing_ok=True)
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def convert_md_to_pdf(md_abs_path: Path, pdf_abs_path: Path) -> str:
    """自动选择可用的转换引擎：WeasyPrint 优先，Word COM 兜底。"""
    errors = []
    try:
        return convert_md_to_pdf_via_weasyprint(md_abs_path, pdf_abs_path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"WeasyPrint: {exc}")
    try:
        return convert_md_to_pdf_via_word(md_abs_path, pdf_abs_path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Word COM: {exc}")
    return f"转换失败: {'; '.join(errors)}。请安装 WeasyPrint 依赖或 Microsoft Word。"