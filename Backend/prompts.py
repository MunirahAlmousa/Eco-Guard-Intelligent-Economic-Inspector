import json

def load_reference_data():
    with open("reference_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

def demographic_prompt(record: dict) -> str:
    return f"""
أنت وكيل ذكاء اصطناعي متخصص في تحليل البيانات الديموغرافية للأسر السعودية.
مهمتك: اكتشاف التناقضات المنطقية في البيانات الديموغرافية.

البيانات المدخلة:
- العمر: {record.get('age')}
- الحالة الاجتماعية: {record.get('marital_status')}
- المؤهل التعليمي: {record.get('education')}
- المهنة: {record.get('occupation')}
- عدد أفراد الأسرة: {record.get('family_size')}

تعليمات التحليل:
1. هل العمر يتناسب مع المؤهل التعليمي؟ (مثال: عمر 20 ودكتوراه = تناقض)
2. هل المهنة تتناسب مع المؤهل التعليمي؟ (مثال: طبيب وثانوية عامة = تناقض)
3. هل الحالة الاجتماعية منطقية مع العمر؟
4. هل حجم الأسرة منطقي؟

مهم جداً: أجب بـ JSON فقط، بدون أي نص قبله أو بعده، بدون كود بلوك، بدون أي شرح.
{{"agent": "الوكيل الديموغرافي", "status": "منطقي أو تناقض مكتشف", "score": 85, "issues": ["مشكلة1"], "notes": "ملاحظة"}}
"""

def financial_prompt(record: dict, reference_data: dict) -> str:
    region = record.get('region', 'الرياض')
    region_data = reference_data.get('regions', {}).get(region,
                  reference_data['regions']['الرياض'])

    housing_electricity = reference_data.get('housing_electricity', {})
    housing_type = record.get('housing_type', 'شقة')
    expected_electricity = housing_electricity.get(housing_type, housing_electricity.get('شقة', {}))

    family_size = record.get('family_size', 1)
    actual_expenses = record.get('actual_expenses', 0)

    if family_size <= 2:
        expected_expenses = 9327
        family_category = "1-2 أفراد"
    elif family_size <= 4:
        expected_expenses = 14797
        family_category = "3-4 أفراد"
    else:
        expected_expenses = 19831
        family_category = "5 أفراد فأكثر"

    expenses_diff = actual_expenses - expected_expenses
    expenses_diff_pct = round((expenses_diff / expected_expenses) * 100, 1) if expected_expenses > 0 else 0

    return f"""
أنت وكيل ذكاء اصطناعي متخصص في تحليل البيانات المالية للأسر السعودية.
مهمتك: اكتشاف التناقضات المالية بالمقارنة مع بيانات هيئة الإحصاء 2023.

البيانات المدخلة:
- الدخل الشهري: {record.get('income')} ريال
- الإنفاق الشهري الفعلي: {actual_expenses} ريال
- نوع السكن: {housing_type}
- فاتورة الكهرباء: {record.get('electricity_bill')} ريال
- عدد أفراد الأسرة: {family_size} ({family_category})
- المنطقة: {region}

البيانات المرجعية من هيئة الإحصاء لمنطقة {region}:
- متوسط الدخل الشهري: {region_data.get('average_income')} ريال
- متوسط الإنفاق الشهري: {region_data.get('average_expenses')} ريال
- متوسط حجم الأسرة: {region_data.get('average_family_size')} أفراد

متوسط الإنفاق الوطني لأسرة {family_category} (هيئة الإحصاء 2023):
- المتوسط المتوقع: {expected_expenses} ريال
- فرق الإنفاق: {expenses_diff:+} ريال ({expenses_diff_pct:+}% عن المتوسط)

فاتورة الكهرباء المتوقعة لـ {housing_type}:
- النطاق: {expected_electricity.get('min')}-{expected_electricity.get('max')} ريال
- المتوسط: {expected_electricity.get('average')} ريال

تعليمات التحليل:
1. هل الدخل منطقي مقارنة بمتوسط المنطقة؟
2. هل فاتورة الكهرباء منطقية لنوع السكن؟
3. هل الإنفاق الفعلي يتناسب مع المتوسط المتوقع لحجم الأسرة؟
4. هل الدخل يكفي لتغطية الإنفاق وإعالة الأسرة في هذه المنطقة؟

مهم جداً: أجب بـ JSON فقط، بدون أي نص قبله أو بعده، بدون كود بلوك، بدون أي شرح.
{{"agent": "الوكيل المالي", "status": "منطقي أو تناقض مكتشف", "score": 85, "issues": ["مشكلة1"], "notes": "ملاحظة"}}
"""

def manager_prompt(demo_result: dict, financial_result: dict, record: dict) -> str:
    demo_issues = ', '.join(demo_result.get('issues', [])) if demo_result.get('issues') else 'لا يوجد'
    financial_issues = ', '.join(financial_result.get('issues', [])) if financial_result.get('issues') else 'لا يوجد'
    demo_score = demo_result.get('score', 0)
    financial_score = financial_result.get('score', 0)

    return f"""
أنت وكيل قيادي متخصص في اتخاذ القرارات النهائية بشأن جودة بيانات الأسر السعودية.
مهمتك: تحليل نتائج الوكيلين وإصدار درجة الموثوقية النهائية.

نتيجة الوكيل الديموغرافي:
- الحالة: {demo_result.get('status', '')}
- الدرجة: {demo_score} / 100
- المشاكل: {demo_issues}
- الملاحظات: {demo_result.get('notes', '')}

نتيجة الوكيل المالي:
- الحالة: {financial_result.get('status', '')}
- الدرجة: {financial_score} / 100
- المشاكل: {financial_issues}
- الملاحظات: {financial_result.get('notes', '')}

بيانات الأسرة:
- المنطقة: {record.get('region', '')}
- الدخل: {record.get('income', 0)} ريال
- الإنفاق الفعلي: {record.get('actual_expenses', 0)} ريال
- نوع السكن: {record.get('housing_type', '')}

قواعد إصدار القرار — اتبعها بدقة:
1. احسب المتوسط الحسابي لدرجتي الوكيلين: ({demo_score} + {financial_score}) / 2
2. إذا كان المتوسط 80 أو أعلى ولا يوجد تناقض واضح في أي وكيل → الحالة: موثوق والدرجة بين 80-100
3. إذا كان المتوسط بين 50 و79 أو يوجد تناقض في وكيل واحد فقط → الحالة: يحتاج مراجعة والدرجة بين 50-79
4. إذا كان المتوسط أقل من 50 أو يوجد تناقضات في كلا الوكيلين → الحالة: مرفوض والدرجة بين 0-49
5. اكتب توصية واضحة ومحددة للباحث الميداني

مهم جداً: أجب بـ JSON فقط، بدون أي نص قبله أو بعده، بدون كود بلوك، بدون أي شرح.
{{"trust_score": 85, "status": "موثوق أو يحتاج مراجعة أو مرفوض", "issues": ["مشكلة1"], "recommendation": "التوصية النهائية"}}
"""
