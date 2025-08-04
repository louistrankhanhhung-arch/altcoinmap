import json

def parse_signal_response(reply):
    try:
        # Nếu GPT trả về dạng JSON đúng, parse trực tiếp
        try:
            data = json.loads(reply.strip().strip("` "))
            # Đổi key thành dạng thống nhất
            result = {k.strip().lower().replace(" ", "_"): v for k, v in data.items()}

            # Convert các trường số
            for k in ["entry_1", "entry_2", "stop_loss"]:
                if k in result:
                    result[k] = float(str(result[k]).replace(",", ""))

            result["tp"] = []
            for i in range(1, 6):
                key = f"tp{i}"
                if key in result:
                    result["tp"].append(float(str(result[key]).replace(",", "")))

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

        required_fields = ["entry_1", "stop_loss", "tp"]
        for field in required_fields:
            if field not in result or not result[field]:
                return None

        return result
    except Exception as e:
        print(f"❌ Error parsing GPT response: {e}")
        return None
