import json
from tools import execute_shell_command


def main(query: str) -> dict:
    out = execute_shell_command("ls -la price_chart.png price_data.json raw_records.json 2>&1")
    info = execute_shell_command("python -c \"import json; d=json.load(open('price_data.json')); print('n_records', len(d['records'])); print('first', d['records'][0]); print('last', d['records'][-1]); print('stats', d['stats'])\" 2>&1")
    return {"answer": out + "\n" + info, "summary": "Verified chart and data files exist and inspected price_data.json contents. Output:\n" + out + "\n" + info}
