# utils.py

def format_prompt_for_gpt(symbol, summary_lines):
    header = f"Analyze {symbol} based on multi-timeframe data:\n"
    body = "\n".join(summary_lines)
    return header + body


def parse_signal_response(reply):
    try:
        lines = reply.strip().splitlines()
        result = {}
        for line in lines:
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, val = line.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            val = val.strip()
            if key in ["entry_1", "entry_2", "stop_loss"]:
                result[key] = float(val.replace(",", ""))
            elif key.startswith("tp"):
                if "tp" not in result:
                    result["tp"] = []
                result["tp"].append(float(val.replace(",", "")))
            elif key == "direction":
                result[key] = val
        return result if "entry_1" in result else None
    except Exception as e:
        print(f"❌ Error parsing GPT response: {e}")
        return None
