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

        # Kiểm tra bắt buộc tối thiểu
        required_fields = ["entry_1", "stop_loss", "tp"]
        for field in required_fields:
            if field not in result or not result[field]:
                return None

        return result
    except Exception as e:
        print(f"❌ Error parsing GPT response: {e}")
        return None
