from typing import Dict, List, Any, Optional

# 預設 PLC 暫存器 Bit 點位樣板定義 (種子資料 / Fallback)
DEFAULT_PLC_BIT_TEMPLATES: Dict[str, Dict[int, Dict[str, Any]]] = {
    # D40016: 同步異常旗標 1 (gv_Error_Mapping1)
    "D40016": {
        0: {"tag": "CMB1_FAULT", "desc": "CMB1 壓縮機1故障", "type": "ALARM", "severity": "ERROR", "need_confirm": True},
        1: {"tag": "CMB2_FAULT", "desc": "CMB2 壓縮機2故障", "type": "ALARM", "severity": "ERROR", "need_confirm": True},
        2: {"tag": "SFB_FAULT", "desc": "SFB 通風故障", "type": "ALARM", "severity": "ERROR", "need_confirm": True},
        3: {"tag": "CFB_FAULT", "desc": "CFB 冷凝器故障", "type": "ALARM", "severity": "ERROR", "need_confirm": True},
        4: {"tag": "EIV_FAULT", "desc": "EIV 緊急換流器故障", "type": "ALARM", "severity": "ERROR", "need_confirm": True},
        5: {"tag": "FADF_FAULT", "desc": "FADF 新鮮空氣擋板關閉故障", "type": "ALARM", "severity": "ERROR", "need_confirm": True},
        6: {"tag": "RAT_FAULT", "desc": "RAT 回風溫度探頭故障", "type": "ALARM", "severity": "ERROR", "need_confirm": True},
        7: {"tag": "ERR_RESERVED_7", "desc": "預留 7", "type": "ALARM", "severity": "INFO", "need_confirm": True},
        8: {"tag": "HP1_FAULT", "desc": "HP1 高壓1故障", "type": "ALARM", "severity": "ERROR", "need_confirm": True},
        9: {"tag": "LP1_FAULT", "desc": "LP1 低壓1故障", "type": "ALARM", "severity": "ERROR", "need_confirm": True},
        10: {"tag": "HP2_FAULT", "desc": "HP2 高壓2故障", "type": "ALARM", "severity": "ERROR", "need_confirm": True},
        11: {"tag": "LP2_FAULT", "desc": "LP2 低壓2故障", "type": "ALARM", "severity": "ERROR", "need_confirm": True},
        12: {"tag": "DPT1_FAULT", "desc": "DPT1 釋壓互感器1故障", "type": "ALARM", "severity": "ERROR", "need_confirm": True},
        13: {"tag": "SPT1_FAULT", "desc": "SPT1 吸入壓互感器1故障", "type": "ALARM", "severity": "ERROR", "need_confirm": True},
        14: {"tag": "DPT2_FAULT", "desc": "DPT2 釋壓互感器2故障", "type": "ALARM", "severity": "ERROR", "need_confirm": True},
        15: {"tag": "SPT2_FAULT", "desc": "SPT2 吸入壓互感器2故障", "type": "ALARM", "severity": "ERROR", "need_confirm": True},
    },
    # D40017: 同步異常旗標 2 (gv_Error_Mapping2)
    "D40017": {
        0: {"tag": "FADC_STATUS", "desc": "FADC 新鮮空氣擋板關閉", "type": "STATUS", "severity": "INFO", "need_confirm": False},
        1: {"tag": "ERR2_RESERVED_1", "desc": "預留 1", "type": "ALARM", "severity": "INFO", "need_confirm": True},
        2: {"tag": "ERR2_RESERVED_2", "desc": "預留 2", "type": "ALARM", "severity": "INFO", "need_confirm": True},
        3: {"tag": "ERR2_RESERVED_3", "desc": "預留 3", "type": "ALARM", "severity": "INFO", "need_confirm": True},
        4: {"tag": "ERR2_RESERVED_4", "desc": "預留 4", "type": "ALARM", "severity": "INFO", "need_confirm": True},
        5: {"tag": "ERR2_RESERVED_5", "desc": "預留 5", "type": "ALARM", "severity": "INFO", "need_confirm": True},
        6: {"tag": "ERR2_RESERVED_6", "desc": "預留 6", "type": "ALARM", "severity": "INFO", "need_confirm": True},
        7: {"tag": "ERR2_RESERVED_7", "desc": "預留 7", "type": "ALARM", "severity": "INFO", "need_confirm": True},
        8: {"tag": "ERR2_RESERVED_8", "desc": "預留 8", "type": "ALARM", "severity": "INFO", "need_confirm": True},
        9: {"tag": "ERR2_RESERVED_9", "desc": "預留 9", "type": "ALARM", "severity": "INFO", "need_confirm": True},
        10: {"tag": "ERR2_RESERVED_10", "desc": "預留 10", "type": "ALARM", "severity": "INFO", "need_confirm": True},
        11: {"tag": "ERR2_RESERVED_11", "desc": "預留 11", "type": "ALARM", "severity": "INFO", "need_confirm": True},
        12: {"tag": "ERR2_RESERVED_12", "desc": "預留 12", "type": "ALARM", "severity": "INFO", "need_confirm": True},
        13: {"tag": "ERR2_RESERVED_13", "desc": "預留 13", "type": "ALARM", "severity": "INFO", "need_confirm": True},
        14: {"tag": "ERR2_RESERVED_14", "desc": "預留 14", "type": "ALARM", "severity": "INFO", "need_confirm": True},
        15: {"tag": "ERR2_RESERVED_15", "desc": "預留 15", "type": "ALARM", "severity": "INFO", "need_confirm": True},
    },
}

SUPPORTED_PLC_REGISTERS = set(DEFAULT_PLC_BIT_TEMPLATES.keys())

def decode_word_bits(word_val: int, bit_map: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    """
    將 16-bit 暫存器數值解碼為各個 bit 的狀態字典
    """
    result = {}
    int_val = int(word_val)
    for bit_index, meta in bit_map.items():
        bit_val = (int_val >> bit_index) & 1
        result[meta["tag"]] = {
            "bitIndex": bit_index,
            "tagName": meta["tag"],
            "tagDesc": meta["desc"],
            "eventType": meta.get("type", "STATUS"),
            "severity": meta.get("severity", "INFO"),
            "value": bit_val
        }
    return result

def detect_word_bit_changes(
    old_word: int,
    new_word: int,
    bit_map: Dict[int, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    利用 XOR 快速找出哪些 Bit 發生了 0->1 或 1->0 變更
    """
    old_val = int(old_word)
    new_val = int(new_word)
    changed_mask = old_val ^ new_val
    if changed_mask == 0:
        return []

    changes = []
    for bit_index in range(16):
        if (changed_mask >> bit_index) & 1:
            prev_bit = (old_val >> bit_index) & 1
            new_bit = (new_val >> bit_index) & 1
            meta = bit_map.get(bit_index, {
                "tag": f"BIT_{bit_index}",
                "desc": f"Bit {bit_index}",
                "type": "STATUS",
                "severity": "INFO"
            })
            
            event_type = meta.get("type", "STATUS")
            if event_type == "ALARM":
                action = "TRIGGERED" if new_bit == 1 else "CLEARED"
            else:
                action = "CHANGED" if new_bit == 1 else "RESTORED"

            changes.append({
                "bitIndex": bit_index,
                "tagName": meta.get("tag", f"BIT_{bit_index}"),
                "tagDesc": meta.get("desc"),
                "eventType": event_type,
                "prevValue": prev_bit,
                "newValue": new_bit,
                "action": action
            })
    return changes
