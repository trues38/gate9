from typing import Dict
import json

def generate_risk_explanation(meta_rag_warning: Dict, original_action: str, final_action: str) -> str:
    """
    Generates a user-friendly explanation for Meta-RAG overrides.
    """
    if not meta_rag_warning:
        return ""
        
    override_level = meta_rag_warning.get('override_level', 'NONE')
    if override_level == 'NONE':
        return ""
        
    # Parse details
    try:
        reason_json = json.loads(meta_rag_warning.get('fail_reason', '{}'))
        fail_type = reason_json.get('fail_type', 'Unknown')
        recurrence = reason_json.get('recurrence_count', 1)
        impact = reason_json.get('impact', 0.0)
        pattern_id = meta_rag_warning.get('origin_pattern_id', 'Unknown')
    except:
        fail_type = "Unknown"
        recurrence = 1
        impact = 0.0
        pattern_id = "Unknown"
        
    # Construct Explanation
    lines = []
    lines.append("[📌 G9 Risk Notice]")
    lines.append(f"- Override: {override_level}")
    
    # Cause
    cause_msg = f"과거 유사 패턴({pattern_id})에서 반복된 손실({recurrence}회)"
    if fail_type == "false_sell":
        cause_msg += " (잘못된 공포 매도)"
    elif fail_type == "false_buy":
        cause_msg += " (잘못된 낙관 매수)"
        
    lines.append(f"- 원인: {cause_msg}")
    
    # System Action
    if original_action != final_action:
        lines.append(f"- 시스템 조치: {original_action} → {final_action}로 변경")
    else:
        lines.append(f"- 시스템 조치: {final_action} 유지 (단, 주의 요망)")
        
    # Recommendation
    rec_msg = "포지션 최소화 및 유동성 확보"
    if override_level == 'SOFT':
        rec_msg = "분할 매매 및 리스크 관리 강화"
        
    lines.append(f"- 권고: {rec_msg}")
    
    return "\n".join(lines)
