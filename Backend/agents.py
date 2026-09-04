import json
import re
import concurrent.futures
from llm_service import call_llm
from prompts import demographic_prompt, financial_prompt, manager_prompt, load_reference_data

_REFERENCE_DATA = load_reference_data()

PERSONAL_FIELDS = ["name", "الاسم", "id", "رقم_الهوية", "phone", "الجوال", "email", "الايميل"]

def anonymize_record(record: dict) -> dict:
    safe_record = {}
    for key, value in record.items():
        if any(personal in key.lower() for personal in PERSONAL_FIELDS):
            continue
        safe_record[key] = value
    return safe_record

def extract_json(text: str) -> str:
    """استخراج أول JSON object من النص"""
    start = text.find('{')
    if start == -1:
        return text
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return text[start:]

def clean_json_string(text: str) -> str:
    """تنظيف النص قبل parse"""
    # إزالة كود بلوك
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    # استخراج الـ JSON
    text = extract_json(text)

    # إزالة أحرف تحكم
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # تحويل علامات الاقتباس العربية والخاصة
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2018', '"').replace('\u2019', '"')
    text = text.replace('\u00ab', '"').replace('\u00bb', '"')

    # إزالة فواصل زائدة
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r',\s*]', ']', text)

    # تحويل السطور الجديدة داخل القيم إلى مسافة
    # لكن بحذر — نحتفظ بهيكل الـ JSON
    text = re.sub(r'\n\s*', ' ', text)

    return text

def fix_arabic_in_json(text: str) -> str:
    """إصلاح النصوص العربية داخل JSON التي قد تحتوي على اقتباسات"""
    # نستبدل أي اقتباس مزدوج داخل قيمة string بـ escaped quote
    def fix_string_values(match):
        key = match.group(1)
        value = match.group(2)
        # نظف القيمة من اقتباسات داخلية
        value = value.replace('"', "'")
        return f'"{key}": "{value}"'
    
    # نحاول إصلاح قيم النصوص
    text = re.sub(r'"([^"]+)":\s*"([^"]*(?:"[^"]*)*)"', fix_string_values, text)
    return text

def parse_json_response(response: str) -> dict:
    """محاولات متعددة لـ parse الـ JSON"""
    original = response

    # المحاولة 1: تنظيف عادي
    try:
        cleaned = clean_json_string(response)
        return json.loads(cleaned)
    except Exception:
        pass

    # المحاولة 2: إصلاح الاقتباسات العربية
    try:
        cleaned = clean_json_string(response)
        fixed = fix_arabic_in_json(cleaned)
        return json.loads(fixed)
    except Exception:
        pass

    # المحاولة 3: regex لاستخراج القيم مباشرة
    try:
        result = {}
        
        # استخراج trust_score أو score
        score_match = re.search(r'"trust_score"\s*:\s*(\d+)', original)
        if score_match:
            result['trust_score'] = int(score_match.group(1))
        
        score_match2 = re.search(r'"score"\s*:\s*(\d+)', original)
        if score_match2:
            result['score'] = int(score_match2.group(1))

        # استخراج status
        status_match = re.search(r'"status"\s*:\s*"([^"]+)"', original)
        if status_match:
            result['status'] = status_match.group(1)

        # استخراج notes
        notes_match = re.search(r'"notes"\s*:\s*"([^"]+)"', original)
        if notes_match:
            result['notes'] = notes_match.group(1)

        # استخراج recommendation
        rec_match = re.search(r'"recommendation"\s*:\s*"([^"]+)"', original)
        if rec_match:
            result['recommendation'] = rec_match.group(1)

        # استخراج issues
        issues_match = re.search(r'"issues"\s*:\s*\[([^\]]*)\]', original)
        if issues_match:
            issues_text = issues_match.group(1)
            issues = re.findall(r'"([^"]+)"', issues_text)
            result['issues'] = issues if issues else []
        else:
            result['issues'] = []

        if result:
            return result

    except Exception:
        pass

    # المحاولة الأخيرة: إرجاع نتيجة افتراضية
    print(f"[parse_json_response FAILED] snippet: {original[:300]}")
    return {
        "status": "يحتاج مراجعة",
        "score": 50,
        "trust_score": 50,
        "issues": ["تعذر تحليل الاستجابة — يرجى المراجعة اليدوية"],
        "notes": "فشل التحليل التلقائي",
        "recommendation": "يرجى مراجعة البيانات يدوياً"
    }

def run_demographic_agent(record: dict) -> dict:
    safe_record = anonymize_record(record)
    prompt = demographic_prompt(safe_record)
    response = call_llm(prompt)
    result = parse_json_response(response)
    result['agent'] = 'الوكيل الديموغرافي'
    return result

def run_financial_agent(record: dict) -> dict:
    safe_record = anonymize_record(record)
    prompt = financial_prompt(safe_record, _REFERENCE_DATA)
    response = call_llm(prompt)
    result = parse_json_response(response)
    result['agent'] = 'الوكيل المالي'
    return result

def run_manager_agent(demo_result: dict, financial_result: dict, record: dict) -> dict:
    safe_record = anonymize_record(record)
    prompt = manager_prompt(demo_result, financial_result, safe_record)
    response = call_llm(prompt)
    result = parse_json_response(response)
    result['agent'] = 'الوكيل القيادي'
    return result

def analyze_record(record: dict) -> dict:
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        demo_future = executor.submit(run_demographic_agent, record)
        financial_future = executor.submit(run_financial_agent, record)
        demo_result = demo_future.result()
        financial_result = financial_future.result()

    manager_result = run_manager_agent(demo_result, financial_result, record)

    return {
        "demographic": demo_result,
        "financial": financial_result,
        "manager": manager_result
    }

def analyze_batch(records: list) -> list:
    results = []
    for i, record in enumerate(records):
        result = analyze_record(record)
        result['record_index'] = i + 1
        result['original_record'] = record
        results.append(result)
    return results
