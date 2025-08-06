import json

def parse_signal_response(reply):
    try:
        # Nếu GPT trả về dạng JSON đúng, parse trực tiếp
        try:
            raw = reply.strip()
            if raw.startswith("```json"):
                raw = raw[7:]  # cắt bỏ "```json\n"
            if raw.endswith("```"):
                raw = raw[:-3]  # cắt bỏ "```"
            data = json.loads(raw.strip())

            # Đổi key thành dạng thống nhất
            result = {k.strip().lower().replace(" ", "_"): v for k, v in data.items()}

            # Convert các trường số
            for k in ["entry_1", "entry_2", "stop_loss"]:
                if k in result:
                    result[k] = safe_float(result[k])

            result["tp"] = []
            for i in range(1, 6):
                key = f"tp{i}"
                if key in result:
                    result["tp"].append(safe_float(result[key]))

            # Đảm bảo có cả nhận định và mã giao dịch nếu có
            result["assessment"] = result.get("nhận_định", result.get("nhận_định_ngắn_gọn", result.get("assessment", "Không có đánh giá")))
            result["pair"] = result.get("symbol", result.get("pair", "UNKNOWN"))

            return result if "entry_1" in result and "stop_loss" in result and result["tp"] else None
        except json.JSONDecodeError:
            pass  # fallback nếu không phải JSON chuẩn

        # Fallback nếu không phải JSON
        lines = reply.strip().splitlines()
        result = {}
        for line in lines:
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, val = line.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            val = val.strip().strip('"').strip("'")

            # Parse các trường số
            if key in ["entry_1", "entry_2", "stop_loss"]:
                try:
                    result[key] = float(val.replace(",", ""))
                except:
                    pass
            elif key.startswith("tp"):
                try:
                    if "tp" not in result:
                        result["tp"] = []
                    result["tp"].append(float(val.replace(",", "")))
                except:
                    pass
            else:
                result[key] = val

        result["assessment"] = result.get("nhận_định", result.get("nhận_định_ngắn_gọn", result.get("assessment", "Không có đánh giá")))
        result["pair"] = result.get("symbol", result.get("pair", "UNKNOWN"))

        required_fields = ["entry_1", "stop_loss", "tp"]
        for field in required_fields:
            if field not in result or not result[field]:
                return None

        return result
    except Exception as e:
        print(f"❌ Error parsing GPT response: {e}")
        return None

def is_safe_dca(trend_4h, trend_1d):
    return (
        (trend_4h == "downtrend" and trend_1d == "uptrend") or
        (trend_4h == "sideways" and trend_1d == "uptrend") or
        (trend_4h == "downtrend" and trend_1d == "sideways")
    )

def safe_float(val):
    try:
        return float(str(val).replace(",", "")) if val not in [None, "None", "null", ""] else None
    except:
        return None
