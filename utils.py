import json

def parse_signal_response(reply):
    try:
        raw = reply.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.endswith("```"):
            raw = raw[:-3]

        data = json.loads(raw)

        # Normalize key format
        result = {k.strip().lower().replace(" ", "_"): v for k, v in data.items()}

        # Force convert required numeric fields
        for k in ["entry_1", "entry_2", "stop_loss"]:
            result[k] = safe_float(result.get(k))

        # Parse tp as list of floats
        result["tp"] = [safe_float(x) for x in result.get("tp", []) if safe_float(x) is not None]

        # Optional fields
        result["assessment"] = result.get("nhan_dinh", result.get("assessment", "Không có đánh giá"))
        result["pair"] = result.get("symbol", result.get("pair", "UNKNOWN"))

        # Check required fields
        required_fields = ["entry_1", "stop_loss"]
        if not isinstance(result.get("tp"), list) or len(result["tp"]) == 0:
            print(f"⚠️ Trường tp không hợp lệ hoặc rỗng -> BỎ QUA")
            return None
        if all(result.get(f) for f in required_fields) and isinstance(result["tp"], list) and len(result["tp"]) > 0:
            return result
        else:
            print(f"⚠️ Dữ liệu thiếu trường bắt buộc: {required_fields} -> BỎ QUA")
            return None

    except json.JSONDecodeError:
        print("⚠️ JSON decode error - fallback to line parsing")
        pass

    # Fallback line parsing
    try:
        lines = reply.strip().splitlines()
        result = {}
        for line in lines:
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            val = val.strip().strip('"').strip("'")

            if key in ["entry_1", "entry_2", "stop_loss"]:
                result[key] = safe_float(val)
            elif key == "tp":
                val = val.strip("[]")
                result["tp"] = [safe_float(x) for x in val.split(",") if safe_float(x) is not None]
            else:
                result[key] = val

        result["assessment"] = result.get("nhan_dinh", result.get("assessment", "Không có đánh giá"))
        result["pair"] = result.get("symbol", result.get("pair", "UNKNOWN"))

        required_fields = ["entry_1", "stop_loss", "tp"]
        if all(result.get(f) for f in required_fields) and isinstance(result["tp"], list) and len(result["tp"]) > 0:
            return result
        else:
            print(f"⚠️ Fallback dữ liệu thiếu trường bắt buộc: {required_fields} -> BỎ QUA")
            return None

    except Exception as e:
        print(f"❌ Error parsing GPT response: {e}")
        return None


def safe_float(val):
    try:
        return float(str(val).replace(",", "")) if val not in [None, "None", "null", ""] else None
    except:
        return None


def is_safe_dca(trend_4h, trend_1d):
    return (
        (trend_4h == "downtrend" and trend_1d == "uptrend") or
        (trend_4h == "sideways" and trend_1d == "uptrend") or
        (trend_4h == "downtrend" and trend_1d == "sideways")
    )
