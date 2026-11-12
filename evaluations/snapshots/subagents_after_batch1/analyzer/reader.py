import re
from llm import call_llm
from tools import execute_shell_command


def main(query: str) -> dict:
    """Read and report the content/headers of a workspace file.
    The query names the file and what to check (e.g. section headers, presence
    of keywords, image validity). Generic utility for verification.
    """
    # crude file extraction from query
    m = re.findall(r"[\w\-]+\.(?:md|json|txt|png|jpg|csv)", query)
    files = list(dict.fromkeys(m)) or ["report.md"]

    report = []
    for fn in files:
        exists = execute_shell_command(f"test -f {fn} && echo YES || echo NO")
        report.append(f"=== {fn} exists: {exists.strip()} ===")
        if fn.lower().endswith((".md", ".txt")):
            heads = execute_shell_command(f"grep -n '^#' {fn} 2>&1")
            report.append(f"headers:\n{heads}")
            size = execute_shell_command(f"wc -c {fn} 2>&1")
            report.append(f"size: {size}")
            tail = execute_shell_command(f"tail -n 40 {fn} 2>&1")
            report.append(f"tail:\n{tail}")
        elif fn.lower().endswith((".png", ".jpg")):
            info = execute_shell_command(f"python -c \"from PIL import Image; im=Image.open('{fn}'); print(im.size, im.mode)\" 2>&1")
            if 'Traceback' in info or 'Error' in info or 'No module' in info:
                info = execute_shell_command(f"file {fn} 2>&1; ls -l {fn} 2>&1")
            report.append(f"image info:\n{info}")

    combined = "\n".join(report)[:6000]
    answer = call_llm(
        system="You verify files. Report clearly: does each file exist, are the image dimensions valid, and does the markdown contain the requested sections/headers? Answer the user's verification question directly.",
        messages=[{"role": "user", "content": f"Verification request: {query}\n\nObserved:\n{combined}"}],
        max_tokens=800,
    )
    return {"answer": answer, "summary": combined}
