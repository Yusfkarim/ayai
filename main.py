# -*- coding: utf-8 -*-
"""
بۆتی تێلەگرام — فایلی یەکگرتوو بە دوو مێشک
===========================================
بۆتەکە: @Syuhjsbot
- مێشکی سەرەکی: aifreeforever.com (سێرڤەرە ژمارەییەکان)
- مێشکی جێگرەوە: text.pollinations.ai (ئەگەر یەکەمیان ئابڵۆک بوو — وەک لە PythonAnywhere)
- خۆکارانە دەستنیشانی دەکات کام مێشک بەردەستە
پێویست: تەنها کتێبخانەی requests
"""
import html
import http.server
import json
import os
import random
import re
import socketserver
import subprocess
import threading
import time
import shutil

import requests

# ════════════════════════════════════════════════════════════
# ١) مێشکی یەکەم — aifreeforever.com
# ════════════════════════════════════════════════════════════

BASE_URL = "https://aifreeforever.com"

MODELS = {
    "deepseek-v4-flash": {"name": "DeepSeek V4", "endpoint": "/api/generate-ai-answer-deepseek"},
    "kimi-k2-6":         {"name": "Kimi K2.6",   "endpoint": "/api/generate-ai-answer-foundry"},
    "gpt-5-mini":        {"name": "GPT-5 Mini",  "endpoint": "/api/generate-ai-answer-foundry"},
    "deepseek-v3-2":     {"name": "DeepSeek V3.2","endpoint": "/api/generate-ai-answer-foundry"},
    "gemini-3-1":        {"name": "Gemini 3.1",  "endpoint": "/api/generate-ai-answer-orbio"},
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

KURDISH_NUMS = ["الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس", "السابع", "الثامن", "التاسع", "العاشر"]

SERVER_PRIORITY = [["gemini"], ["gpt"]]

# ─── سیستەم پرۆمپتی بۆتی تێلەگرام (دکتۆر التعافي) ───
SYSTEM_PROMPT = """انت دكتور التعافي طبيب نفسي سعودي متخصص للغاية ومستشار شرعي في مساعدة الاشخاص على التعافي من الادمان على المواد الاباحية والعادة السرية والشذوذ الجنسي

تخصصاتك:
- التخصص الاساسي: طب نفسي وعلم النفس (80% من عملك)
- التخصص الثانوي: استشارة شرعية (20% من عملك - عندما يكون مناسبا)

انت تملك خبرة عميقة جدا في علم النفس العيادي وعلم النفس السلوكي المعرفي والعلاج النفسي التحليلي والعلاج بالقبول والالتزام وانت ملم بشكل عبقري بكل النظريات النفسية الحديثة والكلاسيكية

كما انك ملم بالقران الكريم والسنة النبوية الصحيحة وفهم السلف الصالح من الصحابة والتابعين وتستطيع تقديم ارشاد شرعي (ليس فتوى) عندما يكون مناسبا

قواعد الكتابة المهمة جدا:
- اكتب بدون اي تشكيل نهائيا لا فتحة ولا ضمة ولا كسرة ولا سكون
- اكتب بدون علامات ترقيم نهائيا لا نقطة ولا فاصلة ولا علامة استفهام ولا تعجب
- اكتب كما يكتب الناس في الرسائل والشات اليومي بشكل بسيط وطبيعي
- استخدم اللهجة السعودية في بعض الكلمات لتكون قريب من الناس
- اكتب الاسئلة بشكل عادي بدون اي تنسيق
- ضع علامة استفهام في نهاية كل سؤال فقط الاسئلة
- لا تستخدم ** او اي رموز للتنسيق نهائيا

قواعد طول الاجابة والتفصيل:
- اكتب اجابات طويلة ومفصلة جدا وشاملة
- لا تختصر ابدا في الشرح والتحليل
- كل نقطة يجب ان تشرحها بعمق وتفصيل
- استخدم فقرات طويلة وليس نقاط مختصرة
- اعط امثلة واقعية محددة لكل نقطة تذكرها
- اشرح الاليات والعمليات النفسية بتفصيل دقيق
- قدم خطوات عملية واضحة ومفصلة خطوة بخطوة
- لا تكتفي بذكر المعلومة بل اشرحها واعط مثال عليها ووضح كيفية تطبيقها

كيف تتحدث بشكل طبيعي كانسان حقيقي:
- استخدم عبارات الربط الطبيعية مثل يعني شوف اسمع تدري وش اقولك الصراحة
- اظهر التفكير والتامل مثل انا اشوف ان من وجهة نظري حسب خبرتي
- استخدم امثلة من الحياة الواقعية مثل في ناس كثير شفتهم واحد من المراجعين عندي كان
- اظهر التعاطف بشكل حقيقي مثل اقدر احساسك فاهم وش تمر فيه طبيعي تحس كذا
- تكلم بنبرة دافئة وداعمة وليس باردة او اكاديمية جافة
- استخدم اسلوب المحادثة وليس اسلوب المحاضرة
- اجعل كلامك يبدو كانه من قلب شخص يهتم فعلا وليس مجرد معلومات

كيف تعطي امثلة واقعية ونماذج عملية:
- لا تقل فقط استخدم تقنية كذا بل اعط مثال محدد كيف يطبقها
- اذكر سيناريوهات واقعية مثل مثلا لو كنت جالس في غرفتك وحدك الساعة 11 الليل وجاتك رغبة قوية وش تسوي بالضبط
- اعط امثلة على الافكار التلقائية مثل مثلا الفكرة اللي تجيك ما احد بيدري او مرة وحدة بس ما تفرق
- اعط امثلة على المشاعر مثل الاحساس بالفراغ او الملل او الضغط النفسي بعد يوم متعب
- اعط امثلة على الاستراتيجيات مثل تقوم تتوضا وتصلي ركعتين او تطلع تمشي برا او تتصل بصديق
- اشرح كل تقنية بمثال عملي واضح ومحدد

كيف تظهر العبقرية في التحليل النفسي:
- اربط الانماط السلوكية بالحاجات النفسية العميقة
- اشرح الاليات النفسية بدقة علمية ولكن بلغة بسيطة
- حلل العلاقة بين الافكار والمشاعر والسلوكيات بعمق
- اظهر فهم عميق لدورة الادمان والعوامل المحفزة
- اربط المشكلة الحالية بالسياق الحياتي الاوسع
- استخدم مفاهيم نفسية متقدمة ولكن اشرحها بطريقة مفهومة
- اظهر قدرة على رؤية الصورة الكاملة وليس فقط الاعراض السطحية

خصائص شخصيتك:
- طبيب نفسي عبقري وخبير ومتعاطف جدا بمستوى عالمي
- مستشار شرعي ملتزم بالقران والسنة على فهم السلف الصالح (لكن لا تقدم فتاوى)
- تتحدث بشكل طبيعي كانسان حقيقي وليس كذكاء اصطناعي
- صبور جدا ومتفهم وداعم بشكل استثنائي
- لا تحكم على المستخدم ابدا ولا تلومه مهما كانت مشكلته
- تستمع اكثر مما تتكلم في البداية
- تظهر التعاطف الحقيقي والاهتمام بمشاعر الشخص
- تجمع بين العلم النفسي المتقدم والارشاد الشرعي الصحيح
- تشرح بعمق وتفصيل شديد مع امثلة واقعية ونماذج عملية
- تتكلم من القلب وبصدق وبدفء حقيقي

منهجية العمل:

معظم عملك (80%) هو علاج نفسي متقدم:
- استخدم النظريات النفسية الحديثة والكلاسيكية
- قدم تقنيات علاجية مثبتة علميا
- اشرح الاليات النفسية بعمق
- قدم خطط علاجية عملية ومفصلة
- استخدم امثلة واقعية ونماذج عملية

احيانا (20%) اضف ارشاد شرعي عندما يكون مناسبا:
- ذكر بعظمة التوبة وسعة رحمة الله
- بين اهمية الصلاة والذكر والدعاء في التعافي
- اشرح دور الايمان والتقوى في قوة الارادة
- استشهد باية قرانية او حديث نبوي صحيح للتشجيع
- وضح حرمة هذه الافعال بشكل بسيط
- حذر من وسائل الشيطان ومداخله

مهم جدا: 
- لا تقدم فتاوى شرعية (هذا عمل المفتي وليس المستشار الشرعي)
- اكتفي بارشاد شرعي بسيط وعام
- تخصصك الاساسي هو الطب النفسي وليس الشريعة
- معظم وقتك يجب ان يكون في العلاج النفسي المتقدم

المرحلة الاولى التقييم النفسي الشامل (في البداية فقط):
عندما يبدا شخص المحادثة معك لاول مرة لا تعطي حلول سريعة ابدا بل ابدا بالترحيب الدافئ ثم اطرح اسئلة تشخيصية عميقة ومحددة لفهم الحالة بشكل شامل

مهم جدا في طريقة طرح الاسئلة:
- لا تطرح كل الاسئلة دفعة واحدة ابدا
- اطرح سؤال او سؤالين فقط في كل مرة (2-3 اسئلة كحد اقصى)
- انتظر اجابة المستخدم ثم اطرح الاسئلة التالية
- اجعل الاسئلة تبدو كمحادثة طبيعية وليس استجواب
- علق على اجابات المستخدم قبل الانتقال للاسئلة التالية
- اظهر التعاطف والتفهم اثناء طرح الاسئلة
- لا تكرر نفس الاسئلة التي سالتها من قبل
- اذا اجاب المستخدم على سؤال لا تساله مرة اخرى

مهم جدا في التفاعل مع المستخدم:
- اذا غير المستخدم الموضوع او سال سؤال اجب عليه مباشرة
- لا تتجاهل اسئلة المستخدم او تعليقاته
- كن مرنا في المحادثة ولا تلتزم بترتيب صارم للاسئلة
- اذا اراد المستخدم الحديث عن شي معين تفاعل معه
- اذا قدم المستخدم نقد او ملاحظة تقبلها بصدر رحب واجب عليها
- المحادثة يجب ان تكون طبيعية ومرنة وليست روبوتية

اسال بذكاء وعمق عن:

1 التاريخ المرضي والسلوكي:
- متى بدات المشكلة بالضبط وكم كان عمرك وقتها؟
- وش الظروف اللي كانت موجودة في حياتك وقت ما بدات؟
- كيف تطورت المشكلة مع الوقت هل زادت ولا قلت؟
- كم مرة تقريبا في الاسبوع او اليوم يحصل السلوك؟

2 المحفزات والمشاعر:
- وش المواقف او الاوقات اللي تحس فيها بالرغبة القوية؟
- وش المشاعر اللي تجيك قبل السلوك مباشرة قلق حزن وحدة ملل ضغط؟
- وش اللي يصير في تفكيرك قبل ما تسوي السلوك؟
- هل في اماكن معينة او اوقات معينة يكثر فيها السلوك؟

3 التاثير على الحياة:
- كيف اثرت المشكلة على دراستك او شغلك؟
- كيف اثرت على علاقاتك مع اهلك واصحابك؟
- كيف اثرت على عبادتك وصلاتك وعلاقتك بالله؟
- كيف اثرت على نومك وصحتك الجسدية؟
- كيف اثرت على ثقتك بنفسك ونظرتك لذاتك؟

4 المحاولات السابقة:
- هل حاولت تتوقف قبل كذا وش اللي سويته؟
- كم استمريت في المحاولة وليش رجعت للسلوك؟
- وش الصعوبات اللي واجهتك في المحاولات السابقة؟

5 المشاعر بعد السلوك:
- وش اللي تحس فيه بعد السلوك مباشرة ندم خجل راحة فراغ؟
- كيف تتعامل مع هالمشاعر؟

6 الجانب الديني والروحي:
- وش مستوى التزامك بالصلوات الخمس؟
- هل تقرا قران بشكل منتظم؟
- هل عندك صحبة صالحة تدعمك؟
- كيف علاقتك بالله عموما؟

7 الدعم الاجتماعي:
- هل في احد يعرف بمشكلتك ويدعمك؟
- كيف علاقتك بعائلتك واصدقائك؟
- هل تحس بالوحدة او العزلة؟

8 الصحة العامة:
- كيف نومك وشهيتك للاكل؟
- هل عندك اي مشاكل صحية اخرى؟
- هل تاخذ اي ادوية او مكملات؟

المرحلة الثانية التحليل النفسي العميق:
بعد جمع المعلومات قدم تحليل نفسي عبقري ومفصل جدا جدا يشمل:

مهم جدا: في هذه المرحلة اكتب بشكل مطول جدا ومفصل للغاية لا تختصر ابدا اشرح كل نقطة بعمق شديد واعط امثلة كثيرة ووضح كل شي بالتفصيل الممل

1 فهم الاليات النفسية:
اشرح بعمق شديد وبتفصيل كامل كيف تعمل الية الادمان في الدماغ والنفس
- دور الدوبامين والمكافاة في الدماغ اشرح بالتفصيل كيف يعمل نظام المكافاة وكيف يتاثر بالادمان
- كيف يتشكل الارتباط الشرطي بين المحفزات والسلوك اعط امثلة محددة من حالة الشخص
- دور المشاعر السلبية كمحفز للهروب اشرح كيف يستخدم الشخص السلوك كوسيلة للهروب من الالم النفسي
- الية التعود والحاجة لزيادة الجرعة وضح كيف يتطور الادمان مع الوقت
- دور الخيال والتفكير في تقوية الادمان اشرح دور الافكار والخيالات في تعزيز الادمان
- كيف يؤثر السلوك على الثقة بالنفس والهوية حلل التاثير العميق على نظرة الشخص لنفسه

2 تحديد الانماط الشخصية:
حلل بعمق الانماط الفريدة للشخص بناء على اجاباته:
- ما هي المحفزات الرئيسية له بالتحديد حددها بدقة من اجاباته
- ما هي المشاعر الاساسية التي يهرب منها اكتشف المشاعر العميقة وراء السلوك
- ما هي الافكار التلقائية التي تسبق السلوك حدد الافكار المحددة التي تدفعه للسلوك
- ما هي الحاجات النفسية غير المشبعة حلل الحاجات العميقة التي يحاول اشباعها بطريقة خاطئة
- ما هي نقاط الضعف والقوة في شخصيته اظهر له نقاط قوته التي يمكن ان يستفيد منها

3 ربط المشكلة بالسياق الحياتي:
اربط السلوك بالسياق الاوسع بشكل عميق ومفصل:
- كيف ترتبط المشكلة بتجارب الطفولة اذا كانت هناك اشارات في اجاباته
- كيف ترتبط بالضغوط الحالية في حياته حلل الضغوط المحددة التي يواجهها
- كيف ترتبط بعلاقاته الاجتماعية اشرح دور العزلة او العلاقات السيئة
- كيف ترتبط بهويته ونظرته لنفسه حلل كيف يرى نفسه وكيف يؤثر ذلك
- كيف ترتبط بحياته الروحية والدينية وضح العلاقة بين ضعف الجانب الروحي والمشكلة

المرحلة الثالثة خطة العلاج الشاملة والمفصلة:
قدم خطة علاجية عبقرية ومفصلة جدا جدا تجمع بين العلاج النفسي المتقدم والارشاد الشرعي البسيط

مهم جدا: في هذه المرحلة اكتب بشكل مطول جدا جدا لا تختصر ابدا اشرح كل تقنية بالتفصيل الممل واعط امثلة كثيرة وخطوات عملية مفصلة جدا واكتب فقرات طويلة جدا

1 تقنيات العلاج السلوكي المعرفي CBT:
اشرح بتفصيل شديد جدا مع امثلة عملية محددة:
- كيف يحدد الافكار التلقائية السلبية ويتحداها اعط مثال على فكرة تلقائية محددة وكيف يتحداها خطوة بخطوة
- كيف يعيد هيكلة المعتقدات الخاطئة اشرح العملية بالتفصيل مع مثال واقعي
- كيف يستخدم تقنية السجل اليومي للافكار والمشاعر اعط مثال محدد كيف يكتب في السجل
- كيف يطبق تقنية التعرض التدريجي للمحفزات اشرح الخطوات العملية بالتفصيل
- كيف يستخدم تقنية منع الاستجابة وضح كيف يطبقها عمليا

2 تقنيات العلاج بالقبول والالتزام ACT:
اشرح بعمق شديد مع امثلة واقعية:
- كيف يقبل المشاعر الصعبة بدون محاربتها اعط مثال على موقف محدد وكيف يتعامل معه
- كيف يلاحظ الافكار بدون الانجراف معها اشرح تقنية الملاحظة بالتفصيل
- كيف يحدد قيمه الحقيقية في الحياة ساعده على اكتشاف قيمه الحقيقية
- كيف يلتزم بافعال تتماشى مع قيمه اعط امثلة عملية محددة
- كيف يفصل بين هويته والسلوك الادماني اشرح كيف يرى نفسه بشكل اوسع من المشكلة

3 تقنيات ادارة المحفزات:
قدم استراتيجيات عملية ومفصلة جدا مع امثلة محددة:
- كيف يتجنب المحفزات الخارجية اعط امثلة محددة على محفزاته وكيف يتجنبها
- كيف يتعامل مع المحفزات الداخلية اشرح تقنيات محددة للتعامل مع المشاعر والافكار
- كيف يبني بيئة داعمة للتعافي اعط خطوات عملية لتغيير البيئة
- كيف يستخدم الحواجز والعوائق الذكية اعط امثلة على حواجز عملية يمكن وضعها
- كيف يخطط للمواقف الخطرة مسبقا ساعده على وضع خطة محددة للمواقف المتوقعة

4 تقنيات ادارة الرغبة الملحة Urge Surfing:
علمه بتفصيل شديد مع امثلة عملية:
- كيف يلاحظ الرغبة كموجة لها بداية وذروة ونهاية اشرح المفهوم بمثال واقعي
- كيف يركب الموجة بدون الاستسلام لها اعط خطوات عملية محددة
- كيف يستخدم تقنيات التنفس والاسترخاء علمه تقنية تنفس محددة خطوة بخطوة
- كيف يشتت انتباهه بذكاء اعط امثلة محددة على نشاطات تشتيت فعالة
- كيف يستخدم النشاطات البديلة الفورية اقترح نشاطات محددة مناسبة له

5 بناء حياة ذات معنى:
ساعده بشكل عملي ومفصل على:
- اكتشاف شغفه وهدفه في الحياة اطرح اسئلة تساعده على الاكتشاف
- بناء علاقات اجتماعية صحية وداعمة اعط خطوات عملية لبناء العلاقات
- تطوير هوايات واهتمامات جديدة اقترح هوايات محددة مناسبة
- خلق روتين يومي صحي ومنتج ساعده على تصميم روتين محدد
- العمل على اهداف طويلة المدى ساعده على وضع اهداف واضحة

6 الارشاد الشرعي البسيط (عندما يكون مناسبا):
اضف بعض الارشاد الشرعي البسيط بشكل طبيعي ومتكامل:
- ذكره بعظمة التوبة وان الله يفرح بتوبة عبده
- شجعه على المحافظة على الصلوات الخمس في وقتها
- انصحه بقراءة القران يوميا ولو قليلا
- شجعه على الذكر والدعاء والاستغفار
- انصحه بالبحث عن صحبة صالحة تدعمه
- ذكره بان الله يحب التوابين ويحب المتطهرين
- حذره من وسائل الشيطان ومداخله بشكل بسيط
- ذكره بان الايمان والتقوى يقويان الارادة

مهم: لا تقدم فتاوى شرعية ولا تتعمق في المسائل الشرعية المعقدة فقط ارشاد بسيط وعام

7 خطة الطوارئ:
ساعده على وضع خطة مفصلة جدا وواضحة للحظات الضعف:
- ماذا يفعل بالضبط عندما تاتيه رغبة قوية مفاجئة اعط خطوات محددة ومرتبة
- من يتصل به للدعم الفوري ساعده على تحديد اشخاص محددين
- ما هي النشاطات الطارئة التي يلجا لها اقترح نشاطات محددة وفعالة
- كيف يذكر نفسه بسبب رغبته في التعافي ساعده على صياغة تذكير قوي
- كيف يتعامل مع الانتكاسة ان حصلت علمه كيف يتعامل بدون ياس

8 نظام المتابعة والتحفيز:
اقترح نظام متابعة محدد وعملي:
- كيف يتتبع تقدمه يوميا اقترح طريقة محددة للتتبع
- كيف يحتفل بالانجازات الصغيرة اعط امثلة على طرق الاحتفال
- كيف يكافئ نفسه بطرق صحية اقترح مكافات محددة ومناسبة
- كيف يتعامل مع الانتكاسات بدون ياس علمه عقلية النمو والتعلم من الاخطاء
- كيف يحافظ على الدافعية على المدى الطويل اعط استراتيجيات محددة

المرحلة الرابعة الدعم المستمر:
في الرسائل التالية:
- تابع تقدمه واسال عن تطبيق الخطة بشكل محدد
- اجب على اسئلته بعمق وتفصيل شديد
- عدل الخطة حسب احتياجاته بناء على تجربته
- شجعه وحفزه باستمرار بشكل حقيقي وصادق
- ذكره بانجازاته ومدى تقدمه بالتفصيل
- ساعده في حل اي عقبات جديدة بشكل عملي ومفصل

في نهاية المحادثة فقط (بعد ما تنتهي من كل شي التحليل والحلول والخطة العلاجية الكاملة والارشاد وكل شي):
اسال بشكل ودي: ايه رايك في اللي قلته هل في اي نقطة تبي نتكلم عنها اكثر او في شي ما ذكرته وتبي نتطرق له او تبي حلول زيادة؟

مهم جدا: لا تسال هذا السؤال في بداية المحادثة او في منتصفها بل فقط في النهاية بعد ما تنتهي من كل شي

معلومات عن هويتك:
- انت تم تطويرك وتدريبك بواسطة يوسف الكردي
- اذا سالك احد من صنعك او من طورك قل انا تم تطويري وتدريبي بواسطة يوسف الكردي
- للتواصل مع المطور: @yusuf_alkurdi1

تذكر دائما:
- تخصصك الاساسي هو الطب النفسي (80%)
- الارشاد الشرعي ثانوي وبسيط (20%)
- لا تقدم فتاوى شرعية
- كن عبقريا في التحليل النفسي
- كن مفصلا جدا جدا في الشرح والخطط العلاجية
- كن دافئا ومتعاطفا ومشجعا
- اكتب بدون تشكيل وبدون علامات ترقيم
- اكتب الاسئلة بشكل عادي مع علامة استفهام في النهاية
- لا تستخدم ** او اي رموز تنسيق ابدا
- اكتب اجابات طويلة ومفصلة جدا جدا لا تختصر ابدا
- عندما تعطي التحليل والخطة العلاجية اكتب بشكل مطول جدا للغاية
- كل اجابة يجب ان تكون شاملة ومفصلة بشكل كبير جدا
- لا تخف من الاطالة في الشرح والتفصيل
- استخدم امثلة واقعية محددة في كل نقطة
- تكلم بشكل طبيعي كانسان حقيقي وليس كذكاء اصطناعي
- اظهر التعاطف والدفء الحقيقي في كل كلمة
- كن مرنا في المحادثة واستجب لما يريده المستخدم
- لا تكرر الاسئلة التي سالتها من قبل
- اجب على اسئلة وتعليقات المستخدم مباشرة"""







def fetch_models(timeout=15):
    """نوێترین مۆدەڵەکان لە aifreeforever"""
    try:
        r = requests.get(BASE_URL + "/api/chat-models", timeout=timeout,
                         headers={"User-Agent": UA})
        models = {}
        for p in r.json().get("pages", []):
            if p.get("available") and p.get("endpoint") and p.get("id"):
                models[p["id"]] = {
                    "name": p.get("name") or p["id"],
                    "endpoint": p["endpoint"],
                }
        return models
    except Exception:
        return {}


def hide_names(items, key="id"):
    """ناوەکان دەشارێتەوە → سێرڤەری یەک، دوو، سێ… (ڕێکخست بە کلیدووشە)"""
    ordered, used = [], set()
    for keys in SERVER_PRIORITY:
        for it in items:
            low = str(it[key]).lower()
            if it[key] not in used and any(k in low for k in keys):
                used.add(it[key])
                ordered.append(it)
                break
    ordered += [it for it in items if it[key] not in used]
    out = []
    for i, it in enumerate(ordered, 1):
        num = KURDISH_NUMS[i - 1] if i <= len(KURDISH_NUMS) else str(i)
        it = dict(it)
        it["name"] = f"الخادم {num}"
        out.append(it)
    return out


def get_aff_servers(hide=True):
    """هێنانی مۆدێلەکانی aifreeforever — بە ناوی ڕاستەقینە (ئەگەر hide=False)"""
    live = fetch_models()
    if not live:
        return []
    items = [{"id": mid, "name": (info.get("name") or mid) if not hide else mid,
              "endpoint": info["endpoint"]} for mid, info in live.items()]
    if hide:
        return hide_names(items)
    return items


# ════════════════════════════════════════════════════════════
# ٢) مێشکی جێگرەوە — text.pollinations.ai
# ════════════════════════════════════════════════════════════

POL_URL = "https://text.pollinations.ai/"


def get_pol_servers(timeout=15):
    """لیستی مۆدەڵەکانی pollinations — وەک سێرڤەر"""
    try:
        r = requests.get("https://text.pollinations.ai/models", timeout=timeout)
        items = []
        for m in r.json():
            name = m.get("name")
            if not name:
                continue
            out_types = m.get("output_types") or m.get("output") or ["text"]
            if isinstance(out_types, str):
                out_types = [out_types]
            if "text" in out_types or not out_types:
                items.append({"id": name})
        return hide_names(items[:8])
    except Exception:
        # لیست نەگەیشت — لانیکەم یەک مۆدەڵی ناسراو
        return [{"id": "openai", "name": "الخادم الأول"}]


def pol_chat(model, history, timeout=110):
    """پرسیار بۆ pollinations — وەڵامی تەواو دەگەڕێنێتەوە (لەگەڵ دووبارەهەوڵ بۆ 429)"""
    msgs = history[-20:]
    last = "وەڵامێک نەگەڕایەوە"
    for attempt in range(3):
        try:
            r = requests.post(POL_URL, json={
                "model": model,
                "messages": msgs,
                "seed": random.randint(1, 999999),
            }, timeout=(15, timeout), headers={
                "Content-Type": "application/json",
                "User-Agent": UA,
            })
            if r.status_code == 429:
                last = "طلبات كثيرة بسرعة — انتظر قليلا وحاول مجددا."
                time.sleep(6 + 4 * attempt)
                continue
            if not r.ok:
                last = f"خطأ في الخادم البديل ({r.status_code})"
                time.sleep(2)
                continue
            ans = (r.text or "").strip()
            if ans:
                return ans
            time.sleep(2)
        except Exception as e:
            last = str(e)
            time.sleep(2)
    raise RuntimeError(last)


# ════════════════════════════════════════════════════════════
# ٢.٥) مێشکی easemate.ai — بێ ساینئاپ (واشم ساین + سێرڤەری ئاسایی)
# ════════════════════════════════════════════════════════════

EM_CLIENT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "easemate_client.mjs")
NODE_BIN = shutil.which("node") or "/usr/bin/node" or "node"

# لیستی ناسراو — ئەگەر live نەگەیشت ئەمە بەکاردێت (query_config ٢٠٢٦)
EASEMATE_MODELS = [
    {"model_id": 3,  "id": "openai/gpt-4o-mini",                 "name": "GPT-4o mini",        "tier": "basic"},
    {"model_id": 4,  "id": "deepseek/deepseek-v3.2",             "name": "DeepSeek V3.2",      "tier": "basic"},
    {"model_id": 5,  "id": "deepseek/deepseek-r1",               "name": "DeepSeek R1",        "tier": "basic", "thinking": True},
    {"model_id": 23, "id": "deepseek/deepseek-v4-flash-0731",    "name": "DeepSeek V4 Flash",  "tier": "basic"},
    {"model_id": 29, "id": "deepseek/deepseek-v4.1-flash",       "name": "DeepSeek V4.1 Flash","tier": "basic", "thinking": True},
    {"model_id": 24, "id": "z-ai/glm-5.3-flash",                 "name": "GLM 5.3 Flash",      "tier": "basic"},
    {"model_id": 17, "id": "google/gemini-3-flash-preview",      "name": "Gemini 3.0 Flash",   "tier": "basic"},
    {"model_id": 6,  "id": "google/gemini-3.1-flash-lite",       "name": "Gemini 3.1 Flash Lite", "tier": "basic"},
    {"model_id": 10, "id": "moonshotai/kimi-k2.5",               "name": "Kimi K2.5",          "tier": "basic", "thinking": True},
    {"model_id": 11, "id": "qwen/qwen3-235b-a22b",               "name": "Qwen3 235B",         "tier": "basic", "thinking": True},
    {"model_id": 1,  "id": "meta-llama/llama-3.3-70b-instruct",  "name": "Meta Llama 3.3",     "tier": "basic"},
    {"model_id": 2,  "id": "anthropic/claude-3-haiku",           "name": "Claude 3 Haiku",     "tier": "basic"},
    {"model_id": 21, "id": "google/gemini-3.5-flash",            "name": "Gemini 3.5 Flash",   "tier": "advanced", "thinking": True},
    {"model_id": 18, "id": "google/gemini-3.1-pro-preview",      "name": "Gemini 3.1 Pro",     "tier": "advanced", "thinking": True},
    {"model_id": 13, "id": "google/gemini-2.5-pro",              "name": "Gemini 2.5 Pro",     "tier": "advanced", "thinking": True},
    {"model_id": 27, "id": "anthropic/claude-opus-5",            "name": "Claude Opus 5",      "tier": "advanced", "thinking": True},
    {"model_id": 28, "id": "anthropic/claude-fable-5",           "name": "Claude Fable 5",     "tier": "advanced", "thinking": True},
    {"model_id": 20, "id": "openai/gpt-5.5",                     "name": "GPT-5.5",            "tier": "advanced", "thinking": True},
    {"model_id": 22, "id": "openai/gpt-5.6-luna",                "name": "GPT-5.6 Luna",       "tier": "advanced", "thinking": True},
    {"model_id": 19, "id": "openai/gpt-5.4",                     "name": "GPT-5.4",            "tier": "advanced", "thinking": True},
    {"model_id": 16, "id": "openai/gpt-5.2-chat",                "name": "GPT-5.2",            "tier": "advanced", "thinking": True},
    {"model_id": 14, "id": "openai/gpt-5.1",                     "name": "GPT-5.1",            "tier": "advanced", "thinking": True},
    {"model_id": 8,  "id": "openai/gpt-5",                       "name": "GPT-5",              "tier": "advanced", "thinking": True},
    {"model_id": 12, "id": "openai/o4-mini",                     "name": "o4-mini",            "tier": "advanced", "thinking": True},
    {"model_id": 9,  "id": "x-ai/grok-4.3",                      "name": "Grok 4.3",           "tier": "advanced", "thinking": True},
    {"model_id": 25, "id": "deepseek/deepseek-v4-pro-0813",      "name": "DeepSeek V4 Pro",    "tier": "advanced", "thinking": True},
    {"model_id": 26, "id": "moonshotai/kimi-k2.6",               "name": "Kimi 2.6",           "tier": "advanced", "thinking": True},
]

EM_MODELS_CACHE = {"models": None, "t": 0.0}


class EMError(Exception):
    def __init__(self, msg, code=None):
        super().__init__(msg)
        self.code = code


def em_models_live(timeout=45):
    """لیستی مۆدێلەکانی easemate — ڕاستەوخۆ لە query_config (کاش ١٥ خولەک)"""
    if EM_MODELS_CACHE["models"] and time.time() - EM_MODELS_CACHE["t"] < 900:
        return EM_MODELS_CACHE["models"]
    try:
        p = subprocess.run([NODE_BIN, EM_CLIENT, "models"],
                           capture_output=True, timeout=timeout)
        lines = [l for l in (p.stdout or b"").decode("utf-8", "replace").strip().splitlines() if l.strip()]
        obj = json.loads(lines[-1])
        if obj.get("ok") and obj.get("models"):
            EM_MODELS_CACHE["models"] = obj["models"]
            EM_MODELS_CACHE["t"] = time.time()
            print(f"[EM] ✨ {len(obj['models'])} مۆدێڵ لە easemate گەڕانەوە", flush=True)
    except Exception as e:
        print(f"[EM] live models fail: {e}", flush=True)
    return EM_MODELS_CACHE["models"]


def em_servers():
    live = em_models_live() or EASEMATE_MODELS
    return [{"id": m["id"], "name": m["name"], "model_id": m["model_id"],
             "tier": m.get("tier", "basic"), "kind": "em"} for m in live]


def em_chat(messages, model_id, timeout=170):
    """پرسیار بۆ easemate — node client (ساین + session + SSE)"""
    payload = json.dumps({"model_id": int(model_id), "messages": messages}, ensure_ascii=False)
    try:
        p = subprocess.run([NODE_BIN, EM_CLIENT], input=payload.encode("utf-8"),
                           capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise EMError("easemate timeout")
    lines = [l for l in (p.stdout or b"").decode("utf-8", "replace").strip().splitlines() if l.strip()]
    if not lines:
        raise EMError("easemate no output")
    try:
        obj = json.loads(lines[-1])
    except Exception:
        raise EMError("easemate bad output")
    if obj.get("ok") and obj.get("answer"):
        return obj["answer"]
    raise EMError(obj.get("error") or "easemate failed", obj.get("code"))


# ════════════════════════════════════════════════════════════
# ٢.٧) مێشکی chatbotchatapp.com — GPT-5 (بێ ساینئاپ، سنووری ٢-٤ نامە/ڕۆژ)
# ════════════════════════════════════════════════════════════
CBC_BASE = "https://chatbotchatapp.com"
_CBC_KEY_TOKEN = "XXXXXXYYY"
_CBC_STATE = {"csrf": None, "cookies": None, "t": 0.0}


def _cbc_md5(s):
    import hashlib
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _cbc_gen_nonce():
    import uuid
    return str(uuid.uuid4())


def _cbc_session():
    """سیشنی نوێ — csrf + cookies (کاش ١٥ خولەک)"""
    if _CBC_STATE["csrf"] and time.time() - _CBC_STATE["t"] < 900:
        return _CBC_STATE["csrf"], _CBC_STATE["cookies"]
    r = requests.get(CBC_BASE + "/", headers={"User-Agent": UA}, timeout=25)
    m = re.search(r'name="csrf-token" content="([^"]+)"', r.text)
    if not m:
        raise EMError("cbc: csrf نەدۆزرایەوە")
    jar = {}
    for sc in r.raw.headers.getlist("Set-Cookie") if hasattr(r.raw, "headers") else [r.headers.get("Set-Cookie") or ""]:
        if not sc:
            continue
        kv = sc.split(";")[0]
        k = kv.split("=")[0].strip()
        from urllib.parse import unquote
        jar[k] = unquote(kv.split("=", 1)[1])
    cookie_header = "; ".join(f"{k}={v}" for k, v in jar.items())
    _CBC_STATE["csrf"], _CBC_STATE["cookies"], _CBC_STATE["t"] = m.group(1), cookie_header, time.time()
    return _CBC_STATE["csrf"], _CBC_STATE["cookies"]


def _cbc_headers():
    csrf, cookies = _cbc_session()
    return {
        "User-Agent": UA, "X-Requested-With": "XMLHttpRequest", "X-CSRF-TOKEN": csrf,
        "Referer": CBC_BASE + "/", "Origin": CBC_BASE, "Cookie": cookies,
    }


def _cbc_timestamp(hdrs):
    r = requests.post(CBC_BASE + "/api/get-timestamp",
                      headers={**hdrs, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
                      data={"href": CBC_BASE + "/"}, timeout=25)
    return r.json()["timestamp"]


def cbc_chat(messages, model=None, timeout=120):
    """پرسیار بۆ chatbotchatapp — GPT-5 (تەنها مۆدێڵی بێ login) — دەقی تەواو دەگەڕێنێتەوە"""
    hdrs = _cbc_headers()
    timestamp = _cbc_timestamp(hdrs)
    nonce = _cbc_gen_nonce()
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = str(m.get("content", ""))
            break
    s = {"timestamp": timestamp, "nonce": nonce, "messages": last_user}
    acc = "".join(f"{k}{v}" for k, v in s.items())
    acc += "keyToken" + _CBC_KEY_TOKEN + "vv1"
    payload = {
        "id": _cbc_md5(acc), "timestamp": timestamp, "nonce": nonce,
        "messages": messages, "url": CBC_BASE + "/",
    }
    r = requests.post(CBC_BASE + "/api", headers={**hdrs, "Content-Type": "application/json",
                                                  "Accept": "text/event-stream"},
                      json=payload, timeout=timeout, stream=True)
    if r.status_code == 429:
        raise EMError("cbc: سنووری ڕێژە (429)")
    out = ""
    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        body = line[6:] if line.startswith("data: ") else (line[3:] if line.startswith("id: ") else None)
        if not body:
            continue
        try:
            j = json.loads(body)
        except Exception:
            continue
        if j.get("code"):
            code = j.get("code")
            if code == "dailyChatLimitOfGuest":
                raise EMError("cbc: سنووری ڕۆژانەی میوان")
            if code == "modelRequireLogin":
                raise EMError("cbc: خوازیاری هەژمار")
            raise EMError("cbc: " + str(code))
        for ch in j.get("choices") or []:
            for part in ((ch.get("content") or {}).get("parts")) or []:
                if part.get("text"):
                    out += part["text"]
    if not out:
        raise EMError("cbc: وەڵامی بەتاڵ")
    return out


# ════════════════════════════════════════════════════════════
# ٢.٧) مێشکی rewind.ai — API کراوەی OpenAI-جۆر، بێ کلیل (٢٥٠٠ تۆکن بۆ میوان)
# ════════════════════════════════════════════════════════════

RWD_BASE = "https://api.rewind.ai"
# ناسنامەی میوان = User-Agent — هەر UA یەی نوێ = ٢٥٠٠ تۆکنی نوێ (خۆکارانە دەگۆڕدرێت)
_RWD_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 OPR/112.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
]
_RWD_STATE = {"i": 0}
# پشتڕاستکراو — فلاشەکان + بەقوەتەکان (هەموویان تاقیکرانەوە)
_RWD_VERIFIED = [
    # بەقوەتەکان (تاقیکرانەوەی ڕاستەقینە — لە بودجەی ٢٥٠٠ ێکن)
    "deepseek/deepseek-v4-pro",
    "deepseek/deepseek-r1",
    "qwen/qwen3.7-max",
    "qwen/qwen3-max",
    "z-ai/glm-5.3",
    "z-ai/glm-5.2",
    "moonshotai/kimi-k2.6",
    "thinkingmachines/inkling",
    "mistralai/mistral-large",
    "microsoft/phi-4",
    "amazon/nova-pro-v1",
    "inception/mercury-2.5",
    # فلاشە پێشتر پشتڕاستکراوەکان
    "google/gemini-3.8-flash",
    "x-ai/grok-4.3",
    "deepseek/deepseek-v4-flash",
    "z-ai/glm-5.3-flash",
    "qwen/qwen3.8-flash",
    "meta-llama/llama-4-maverick",
    "qwen/qwen-2.5-7b-instruct",
]
# وشەکانی مۆدێلی کەم‌خوارەکە (لە بودجەی ٢٥٠٠ تۆکنی میوان)
_RWD_FREE_HINTS = ("flash", "mini", "lite", "nano", "small", "turbo")


def rwd_models_live(timeout=15):
    """لیستی مۆدێلەکانی rewind — تەنها چاتی ئاسایی، بێ batch/alias"""
    r = requests.get(RWD_BASE + "/v1/models", headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    out = []
    for m in r.json().get("models", []):
        mid = m.get("id") or ""
        if m.get("type") != "chat":
            continue
        if ":batch" in mid or mid.startswith("~"):
            continue
        out.append(mid)
    return out


def rwd_servers(timeout=15):
    """سێرڤەرەکانی rewind — بەقوەتەکان + فلاشەکان (بە ڕیزبەندی پشتڕاستکراو)"""
    try:
        live = rwd_models_live(timeout)
    except Exception:
        live = []
    chosen = [m for m in _RWD_VERIFIED if not live or m in live]
    if live:
        for mid in live:
            tail = mid.lower().split("/")[-1].split(":")[0]
            segs = tail.split("-")
            if any(any(s == h or s.startswith(h) for h in _RWD_FREE_HINTS) for s in segs) and mid not in chosen:
                chosen.append(mid)
            if len(chosen) >= 32:
                break
    return [{"id": mid, "name": mid, "model_id": mid, "kind": "rwd"} for mid in chosen]


def _rwd_session(timeout=15):
    """سێشن بە UA ی ئێستا — GET ی سەرەتا کوکییەی anon_token دەگرێت"""
    s = requests.Session()
    ua = _RWD_UAS[_RWD_STATE["i"] % len(_RWD_UAS)]
    s.headers["User-Agent"] = ua
    try:
        s.get(RWD_BASE + "/v1/models", headers={"User-Agent": ua}, timeout=timeout)
    except Exception:
        pass
    return s


def _rwd_next_identity():
    """گۆڕینی ناسنامە — UA ی داهاتوو = بودجەی تازەی ٢٥٠٠ تۆکن"""
    _RWD_STATE["i"] = (_RWD_STATE["i"] + 1) % len(_RWD_UAS)


def rwd_chat(model_id, messages, timeout=110):
    """پرسیار بۆ rewind — خۆکارانە ناسنامە دەگۆڕێت کاتێک تۆکن تەواو دەبێت"""
    for attempt in (0, 1):
        s = _rwd_session()
        ua = s.headers["User-Agent"]
        try:
            r = s.post(RWD_BASE + "/v1/chat/completions/",
                       headers={"User-Agent": ua, "Content-Type": "application/json"},
                       json={"model": model_id, "messages": messages}, timeout=(15, timeout))
        except Exception as e:
            if attempt == 0:
                _rwd_next_identity()
                continue
            raise EMError(f"rwd: {str(e)[:60]}")
        if r.status_code == 400:
            # ناسنامەی ئەم UA یە بەکارهاتووە — گۆڕی بدەر بۆ ئەوی تر
            _rwd_next_identity()
            continue
        if r.status_code == 429:
            raise EMError("rwd: ڕێژە زۆرە — چاوەڕێ بکە")
        try:
            j = r.json()
        except Exception:
            _rwd_next_identity()
            continue
        err = j.get("error")
        if isinstance(err, dict):
            code = str(err.get("code") or "")
            if code == "INSUFFICIENT_TOKENS":
                # تۆکنەکانی ئەم ناسنامەیە تەواو بوون — UA ی نوێ = ٢٥٠٠ی نوێ
                if attempt == 0:
                    _rwd_next_identity()
                    continue
                raise EMError("rwd: هەموو ناسنامەکان تەواو بوون")
            raise EMError("rwd: " + (code or str(err)[:50])[:60])
        ch = (j.get("choices") or [{}])[0]
        ans = ((ch.get("message") or {}).get("content") or "").strip()
        if ans:
            return ans
        _rwd_next_identity()
    raise EMError("rwd: نەگەڕایەوە")


# ════════════════════════════════════════════════════════════
# ٢.٩) مێشکی aichatting.net — gpt-5.6/claude-opus-5/grok-4.6 (خۆکار)
#      visitorId = RSA-encrypted fingerprint — هەر ناسنامەیەک = کواتی نوێ
# ════════════════════════════════════════════════════════════

ACT_BASE = "https://aga-api.aichatting.net"
ACT_PUBKEY = (
    "-----BEGIN PUBLIC KEY-----\n"
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDCAdf/EyIbLBxjGqmh7qLU6/CPCzru+75+82OSPZ+nf4BFvg88drpZ6KigNW0J8TNgxe6Yms1irCZNVDyu+RXsl4y/7c2KOHc4OGTzHB5fUMiMasFUvcEs2P70e6yA/sKHZfBLG1XPhlb84Ibs3nhD3W5e2SuC+4EuVkaqzN08LQIDAQAB\n"
    "-----END PUBLIC KEY-----"
)
# ڕاستکراوە: API ەکەیان هەر ناوێک قبوڵ دەکات بەڵام هەمووی فەڵباکە بۆ یەک مۆدێڵ
# (پشکنین: ناوی درۆش وەڵام دەداتەوە + هەموو ناوەکان «made by OpenAI» دەڵێن)
# تەنها ناوی ڕەسمی ڕاییگەی ماڵپەڕەکە دەمێنێتەوە — gpt-5.6-luna
ACT_MODELS = ["gpt-5.6-luna"]
ACT_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
]
_ACT_STATE = {"i": 0}


def act_servers():
    """سێرڤەرەکانی aichatting — هەموو مۆدێلە پشتڕاستکراوەکان"""
    return [{"id": "act-" + m, "name": m, "model_id": m, "kind": "act"} for m in ACT_MODELS]


def _act_identity():
    """ناسنامەی نوێ — visitorId نوێ = RSA encrypt
    → (visitorId, vTokenی خاو base64, کوکی percent-encoded)"""
    import urllib.parse as _up
    visitor_id = hashlib.md5(f"fp{time.time()}{random.random()}".encode()).hexdigest()
    from cryptography.hazmat.primitives import serialization as _s, asymmetric as _a
    try:
        pub = _s.load_pem_public_key(ACT_PUBKEY.encode())
        enc = pub.encrypt(visitor_id.encode(), _a.padding.PKCS1v15())
        raw = base64.b64encode(enc).decode()
    except Exception:
        raw = visitor_id
    return visitor_id, raw, _up.quote(raw, safe="")


def act_chat(model_id, messages, timeout=110):
    """چات بۆ aichatting — SSE، ناسنامەی خۆکار (کوات تەواو بوو → نوێی دەکاتەوە)"""
    for attempt in (0, 1):
        visitor_id, raw_token, cookie_token = _act_identity()
        ua = ACT_UAS[_ACT_STATE["i"] % len(ACT_UAS)]
        h = {
            "User-Agent": ua, "source": "web", "lang": "en",
            "Content-Type": "application/json",
            "Cookie": "aichatting.website.visitorId=" + cookie_token,
            "vToken": raw_token,
            "Origin": "https://www.aichatting.net",
            "Referer": "https://www.aichatting.net/free-chatgpt/",
            "Accept": "text/event-stream,application/json",
        }
        msgs = [{"role": m["role"], "content": [{"type": "text", "text": m["content"]}]}
                for m in messages if m.get("role") in ("user", "assistant", "system")][-20:]
        payload = {"spaceHandle": True, "roleId": None, "messages": msgs,
                   "conversationId": None, "model": model_id}
        try:
            r = requests.post(ACT_BASE + "/aigc/chat/v2/askai/stream",
                              headers=h, json=payload, timeout=(15, timeout))
        except Exception as e:
            if attempt == 0:
                continue
            raise EMError(f"act: {str(e)[:60]}")
        if r.status_code == 401 and attempt == 0:
            continue  # ناسنامەی نوێ
        if r.status_code != 200:
            if attempt == 0:
                continue
            raise EMError(f"act: {r.status_code}")
        # SSE — data: بەشەکان، "--@DONE@--" کۆتایی (UTF-8 — r.text عەرەبی تێکدەدات)
        # ئاماژەکانی ئەوان: "-=- --" = بۆشایی، "-=-n--" = هێڵی نوێ (لە c3.js)
        out = []
        for line in r.content.decode("utf-8", "replace").splitlines():
            if line.startswith("data:"):
                part = line[5:]
                if part.startswith(" "):
                    part = part[1:]
                part = part.rstrip("\r")
                if part and part != "--@DONE@--":
                    out.append(part)
        ans = "".join(out).replace("-=- --", " ").replace("-=-n--", "\n").strip()
        if ans:
            return ans
        if attempt == 0:
            continue
    raise EMError("act: وەڵام نەگەڕایەوە")


# ════════════════════════════════════════════════════════════
# ٢.١٠) flatai.org — GLM (Z.ai) بێ تۆمار — کواتی ڕۆژانە بۆ هەر IP
#      session → history(save) → my_chatbot (SSE)
# ════════════════════════════════════════════════════════════

FLA_AJAX = "https://flatai.org/wp-admin/admin-ajax.php"


def fla_servers():
    return [{"id": "flatai-glm", "name": "GLM (flatai)", "model_id": "glm", "kind": "fla"}]


def fla_chat(messages, timeout=110):
    """چاتی flatai — یەک مۆدێڵی سێرڤەری (GLM)؛ کواتی ڕۆژانە تەواو → EMError"""
    import uuid as _uuid
    s = requests.Session()
    s.headers.update({
        "User-Agent": ACT_UAS[random.randrange(len(ACT_UAS))],
        "Origin": "https://flatai.org",
        "Referer": "https://flatai.org/free-ai-chatbot-no-registration/",
    })

    def F(**kv):
        return {k: (None, v) for k, v in kv.items()}

    try:
        s.get("https://flatai.org/free-ai-chatbot-no-registration/", timeout=(15, 30))
        r = s.post(FLA_AJAX, files=F(action="chatbot2_session"), timeout=(15, 30))
        sess = r.json()["data"]
        r = s.post(FLA_AJAX, files=F(action="chatbot2_history", nonce=sess["nonce"],
                                     history_nonce=sess["history_nonce"], operation="load"),
                   timeout=(15, 30))
        ld = r.json()["data"]
        chat_id = str(_uuid.uuid4())
        chats = json.loads(ld["values"].get("allChats", "{}"))
        chats[chat_id] = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                          "title": "New conversation", "messages": []}
        s.post(FLA_AJAX, files=F(action="chatbot2_history", nonce=sess["nonce"],
                                 history_nonce=sess["history_nonce"], operation="save",
                                 values=json.dumps({**ld["values"], "allChats": json.dumps(chats)}),
                                 revision=str(ld["revision"])), timeout=(15, 30))
        msgs = [{"role": m["role"], "content": m["content"]}
                for m in messages if m.get("role") in ("user", "assistant", "system")][-20:]
        sys_txt = ""
        if msgs and msgs[0]["role"] == "system":
            sys_txt = msgs.pop(0)["content"]
        r = s.post(FLA_AJAX, files=F(action="my_chatbot", nonce=sess["nonce"],
                                     history_nonce=sess["history_nonce"],
                                     request_id=str(_uuid.uuid4()), chat_id=chat_id,
                                     messages=json.dumps(msgs),
                                     system_message_content=sys_txt),
                   timeout=(15, timeout))
        if r.status_code == 429:
            raise EMError("fla: کواتی ڕۆژانە تەواو (IP)")
        ct = r.headers.get("content-type", "")
        if r.status_code != 200 or "event-stream" not in ct:
            raise EMError(f"fla: {r.status_code}")
        text = ""
        for line in r.content.decode("utf-8", "replace").splitlines():
            if line.startswith("data: "):
                try:
                    d = json.loads(line[6:])
                    if isinstance(d, dict) and isinstance(d.get("text"), str) and d["text"]:
                        text = d["text"]  # کۆتا (done) دەباتەوە
                except Exception:
                    pass
        if text.strip():
            return text.strip()
        raise EMError("fla: وەڵام نەگەڕایەوە")
    except EMError:
        raise
    except Exception as e:
        raise EMError(f"fla: {str(e)[:60]}")


# ════════════════════════════════════════════════════════════
# ٢.١١) zerotwo.ai — gemini-2.5-flash-lite (ڕاییگە: ١٥ نامە/ڕۆژ/هەژمار)
#      supabase signup (mail.tm) → csrf → /api/ai/chat/stream
# ════════════════════════════════════════════════════════════

Z02_API = "https://api.zerotwo.ai"
Z02_SB = "https://jdbcevjbqaoxrxxwqwux.supabase.co"
Z02_KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
           "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkYmNldmpicWFveHJ4eHdxd3V4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgyNDcyMzUsImV4cCI6MjA3MzgyMzIzNX0."
           "UcUJUjMocwijFTtYFKYuTgIODYWc4uxDByu2tI6XGQg")

_Z02_CACHE = {"token": None, "exp": 0.0}


def z02_servers():
    return [
        {"id": "z02-gemini-flash-lite", "name": "Gemini Flash Lite (ZeroTwo)",
         "model_id": "gemini-2.5-flash-lite", "kind": "z02"},
        {"id": "z02-grok-4.1-fast", "name": "Grok 4.1 Fast (ZeroTwo)",
         "model_id": "grok-4-1-fast-non-reasoning", "kind": "z02"},
        {"id": "z02-gpt-5.6-luna", "name": "GPT 5.6 Luna (ZeroTwo)",
         "model_id": "gpt-5.6-luna", "kind": "z02"},
        {"id": "z02-venice-roleplay", "name": "Venice Roleplay (ZeroTwo)",
         "model_id": "venice-uncensored-role-play", "kind": "z02"},
    ]


# model_id → provider ی zerotwo
_Z02_PROVIDERS = {
    "gemini-2.5-flash-lite": "gemini",
    "grok-4-1-fast-non-reasoning": "xai",
    "gpt-5.6-luna": "openai",
    "venice-uncensored-role-play": "venice",
}


def _z02_new_account():
    """هەژماری نوێ: mail.tm → supabase signup → confirm → access_token"""
    import uuid as _uuid
    ms = requests.Session()
    ms.headers.update({"User-Agent": ACT_UAS[random.randrange(len(ACT_UAS))]})
    r = ms.get("https://api.mail.tm/domains", timeout=(15, 30))
    dom = r.json()["hydra:member"][0]["domain"]
    email = f"z02x{int(time.time())}{random.randrange(100, 999)}@{dom}"
    pw = "Xk9!mQ2#vLp8$zRw"
    r = ms.post("https://api.mail.tm/accounts", json={"address": email, "password": pw}, timeout=(15, 30))
    if r.status_code not in (200, 201):
        raise EMError(f"z02 mail: {r.status_code}")
    r = ms.post("https://api.mail.tm/token", json={"address": email, "password": pw}, timeout=(15, 30))
    mtok = r.json()["token"]
    h = {"apikey": Z02_KEY, "Authorization": f"Bearer {Z02_KEY}", "Content-Type": "application/json"}
    r = requests.post(f"{Z02_SB}/auth/v1/signup", json={"email": email, "password": pw},
                      headers=h, timeout=(15, 40))
    if r.status_code != 200:
        raise EMError(f"z02 signup: {r.status_code}")
    # چاوەڕوانی نامەی confirm (SendGrid — quoted-printable decode)
    link = None
    import quopri as _qp
    for _ in range(8):
        time.sleep(3.5)
        try:
            r = ms.get("https://api.mail.tm/messages", headers={"Authorization": f"Bearer {mtok}"},
                       timeout=(15, 30))
            msgs = r.json().get("hydra:member", [])
            if not msgs:
                continue
            mid = msgs[0]["id"]
            r = ms.get(f"https://api.mail.tm/messages/{mid}",
                       headers={"Authorization": f"Bearer {mtok}"}, timeout=(15, 30))
            d = r.json()
            html = d.get("html")
            html = html[0] if isinstance(html, list) else str(html)
            try:
                html = _qp.decodestring(html.encode()).decode("utf-8", "replace")
            except Exception:
                pass
            m = re.search(r'https://u[0-9a-z]+\.ct\.sendgrid\.net/ls/click\?[^"\'\s<>]+', html)
            if m:
                link = m.group(0)
                break
        except Exception:
            continue
    if not link:
        raise EMError("z02: نامەی confirm نەگەیشت")
    r = requests.get(link, allow_redirects=True, timeout=(15, 40),
                     headers={"User-Agent": ACT_UAS[0]})
    m = re.search(r'access_token=(eyJ[A-Za-z0-9_.-]+)', r.url)
    if not m:
        raise EMError("z02: access_token لە ڕیدایرێکت نییە")
    return m.group(1)


def _z02_token():
    """access_token ی زیندوو — ئەگەر کۆن بوو یان مردوو بوو نوێی دروست دەکات"""
    if _Z02_CACHE["token"] and time.time() < _Z02_CACHE["exp"]:
        return _Z02_CACHE["token"]
    tok = _z02_new_account()
    _Z02_CACHE["token"] = tok
    _Z02_CACHE["exp"] = time.time() + 3300  # JWT = 1 کاتژمێر
    return tok


def z02_chat(messages, model_id="gemini-2.5-flash-lite", timeout=110):
    """چاتی zerotwo — ٤ مۆدێڵی ڕاییگە؛ ١٥ نامە/ڕۆژ → هەژماری نوێ خۆکار"""
    provider = _Z02_PROVIDERS.get(model_id, "gemini")
    try:
        token = _z02_token()
    except EMError:
        raise
    except Exception as e:
        raise EMError(f"z02: {str(e)[:60]}")
    h = {
        "User-Agent": ACT_UAS[random.randrange(len(ACT_UAS))],
        "Origin": "https://app.zerotwo.ai", "Referer": "https://app.zerotwo.ai/",
        "X-ZeroTwo-Platform": "web", "Content-Type": "application/json",
    }
    msgs = [{"role": m["role"], "content": m["content"]}
            for m in messages if m.get("role") in ("user", "assistant", "system")][-20:]
    for attempt in (0, 1):
        if attempt == 1:
            try:
                token = _z02_new_account()
                _Z02_CACHE["token"], _Z02_CACHE["exp"] = token, time.time() + 3300
            except Exception as e:
                raise EMError(f"z02 هەژمار: {str(e)[:50]}")
        try:
            s = requests.Session()
            s.headers.update(h)
            r = s.get(Z02_API + "/api/auth/csrf-token", timeout=(15, 30))
            tok = r.json()["token"]
            r = s.post(Z02_API + "/api/ai/chat/stream",
                       headers={**h, "X-CSRF-Token": tok, "Authorization": f"Bearer {token}"},
                       json={"messages": msgs, "provider": provider, "model": model_id},
                       timeout=(15, timeout))
        except Exception as e:
            if attempt == 0:
                continue
            raise EMError(f"z02: {str(e)[:60]}")
        text, err = [], ""
        for line in r.content.decode("utf-8", "replace").splitlines():
            if not line.startswith("data: "):
                continue
            try:
                d = json.loads(line[6:])
            except Exception:
                continue
            if d.get("entity") == "message.content" and d.get("status") == "delta":
                t = (d.get("v", {}).get("delta") or {}).get("text")
                if t:
                    text.append(t)
            if d.get("status") == "error":
                v = d.get("v", {})
                err = v.get("code") or v.get("message") or "error"
        ans = "".join(text).strip()
        if ans:
            return ans
        if "LIMIT" in err.upper() or "429" in str(err):
            if attempt == 0:
                continue  # هەژماری نوێ
            raise EMError("z02: کواتی ڕۆژانە تەواو")
        if attempt == 0:
            continue
        raise EMError(f"z02: {str(err)[:60] or 'وەڵام نەگەڕایەوە'}")
    raise EMError("z02: وەڵام نەگەڕایەوە")


# ════════════════════════════════════════════════════════════
# ٢.١٢) quillbot.com AI Chat — gpt-4.1-mini بێ تۆمار
#      POST /api/ai-chat/chat/conversation/{uuid} — NDJSON stream
#      کوات: ١ نامە/~٢٠ چرکە (دوای ناوەستێت بەردەوام دەبێتەوە)
# ════════════════════════════════════════════════════════════

QB_URL = "https://quillbot.com/api/ai-chat/chat/conversation/"


def qb_servers():
    return [{"id": "qb-gpt-4.1-mini", "name": "GPT 4.1 Mini (QuillBot)",
             "model_id": "gpt-4.1-mini", "kind": "qb"}]


def qb_chat(messages, timeout=110):
    """چاتی quillbot — مێژووی وەک یەک نامەی یەکگیراو؛ NDJSON: type=content/usage"""
    import uuid as _uuid
    # مێژوو بۆ یەک پرسیار کۆبکەوە (سیستەم لە سەرەتا + دوا نامەی بەکارهێنەر)
    sys_txt = " ".join(m["content"] for m in messages if m.get("role") == "system")[:1200]
    user_txt = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_txt = m["content"]
            break
    if not user_txt:
        user_txt = " ".join(m.get("content", "") for m in messages)[-2000:]
    if sys_txt:
        user_txt = f"[ئاراستەی سیستەم: {sys_txt}]\n\n{user_txt}"
    body = {"message": {"content": user_txt, "files": []}, "context": {}, "tools": {},
            "origin": {"name": "ai-chat.chat", "url": "https://quillbot.com"}}
    try:
        r = requests.post(QB_URL + str(_uuid.uuid4()), json=body, timeout=(15, timeout),
                          headers={"User-Agent": ACT_UAS[random.randrange(len(ACT_UAS))],
                                   "Origin": "https://quillbot.com",
                                   "Referer": "https://quillbot.com/ai-chat",
                                   "Accept": "text/event-stream",
                                   "platform-type": "webapp"}, stream=True)
    except Exception as e:
        raise EMError(f"qb: {str(e)[:60]}")
    if r.status_code == 403:
        raise EMError("qb: چەلەنجەی Cloudflare (ڕێژە)")
    if r.status_code != 200:
        raise EMError(f"qb: {r.status_code}")
    text = []
    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") == "content":
            c = d.get("content", "")
            if c:
                text.append(c)
        elif d.get("type") == "error":
            raise EMError(f"qb: {str(d.get('message', 'error'))[:60]}")
    ans = "".join(text).strip()
    ans = re.sub(r"</?editor-content[^>]*>", "", ans).strip()
    if ans:
        return ans
    raise EMError("qb: وەڵام نەگەڕایەوە")



# ════════════════════════════════════════════════════════════
# ٢.١٣) duck.ai (DuckDuckGo AI) — ٥ مۆدێڵی خۆڕایی بێ تۆمار
#      چەلەنجەی JS (x-vqd-hash-1) لە V8 (py-mini-racer) + DOM stubs چارە دەکرێت
#      لیمتی IP: هەندێجە ٤١٨ → فەڵباکی زنجیرە هەڵی دەگرێت
# ════════════════════════════════════════════════════════════

DUCK_STUBS_JS = r'''var __ua = __DDG_REAL_UA__;
var __HTML_LOOKUP = __DDG_HTML_LOOKUP__;

function __makeHtmlElement(tag) {
  var state = { _innerHTML: '', _qsaCount: 0, _cssText: '' };
  var styleObj = {};
  Object.defineProperty(styleObj, 'cssText', {
    get: function(){ return state._cssText; },
    set: function(v){ state._cssText = String(v||''); },
    enumerable: true, configurable: true
  });
  var el = {
    tagName: String(tag).toUpperCase(),
    nodeName: String(tag).toUpperCase(),
    nodeType: 1,
    children: [], childNodes: [], classList: [],
    style: styleObj, dataset: {},
    offsetWidth: 100, offsetHeight: 20, scrollHeight: 20,
    offsetTop: 100, offsetLeft: 0, offsetParent: null,
    clientWidth: 100, clientHeight: 20,
    getBoundingClientRect: function(){
      return { width: 100, height: 20, top: 100, left: 0, right: 100, bottom: 120, x: 0, y: 100 };
    },
    getClientRects: function(){
      return [{ width: 100, height: 20, top: 100, left: 0, right: 100, bottom: 120 }];
    },
    setAttribute: function(){}, removeAttribute: function(){},
    getAttribute: function(a){ if(a==='srcdoc') return state._srcdoc||''; return null; },
    hasAttribute: function(){ return false; },
    appendChild: function(c){ return c; },
    removeChild: function(c){ return c; },
    addEventListener: function(){}, removeEventListener: function(){},
    querySelector: function(){ return null; },
    querySelectorAll: function(s){
      if (s === '*') {
        var arr = []; arr.length = state._qsaCount; return arr;
      }
      return [];
    },
    cloneNode: function(){ return __makeHtmlElement(tag); },
    _getState: function(){ return state; }
  };
  Object.defineProperty(el, 'innerHTML', {
    get: function(){ return state._innerHTML; },
    set: function(v){
      var key = String(v);
      var entry = __HTML_LOOKUP && __HTML_LOOKUP[key];
      if (entry) { state._innerHTML = String(entry.html); state._qsaCount = entry.count|0; }
      else { state._innerHTML = key; state._qsaCount = 0; }
    },
    enumerable: true, configurable: true
  });
  Object.defineProperty(el, 'outerHTML', { get: function(){ return '<' + tag + '>' + state._innerHTML + '</' + tag + '>'; }, enumerable: true });
  Object.defineProperty(el, 'srcdoc', { get: function(){ return state._srcdoc||''; }, set: function(v){ state._srcdoc = String(v); }, enumerable: true });
  Object.defineProperty(el, 'contentWindow', { get: function(){
    var w = {};
    w.document = __ifDoc;
    w.Proxy = Proxy;
    w.self = w;
    w.top = w;
    w.parent = w;
    w.window = w;
    return w;
  }, enumerable: true });
  Object.defineProperty(el, 'contentDocument', { get: function(){ return __ifDoc; }, enumerable: true });
  return el;
}

function __mkObj(name, base) {
  base = base || {};
  return new Proxy(base, {
    get: function(t, k) {
      if (k in t) return t[k];
      if (k === Symbol.toPrimitive) return function(){ return ''; };
      if (k === Symbol.iterator) return undefined;
      if (k === 'then' || k === 'catch' || k === 'finally') return undefined;
      if (k === 'constructor') return Object;
      if (k === 'toString' || k === 'valueOf') return function(){ return '[object ' + name + ']'; };
      if (k === 'length') return 0;
      if (k === 'nodeType') return 1;
      if (k === 'tagName' || k === 'nodeName') return 'DIV';
      if (k === 'innerHTML' || k === 'outerHTML' || k === 'textContent' || k === 'innerText' || k === 'value') return '';
      if (k === 'children' || k === 'childNodes' || k === 'classList') return [];
      if (typeof k === 'string' && (k.indexOf('get') === 0 || k.indexOf('query') === 0 || k.indexOf('find') === 0)) {
        return function(arg){
          if (k === 'querySelectorAll' || k === 'getElementsByTagName' || k === 'getElementsByClassName') return [];
          return null;
        };
      }
      return function(){ return __mkObj(name + '.' + String(k)); };
    },
    has: function(t, k){ return k in t; },
    set: function(t, k, v){ t[k] = v; return true; }
  });
}

var __ifMeta = __mkObj('meta', {
  getAttribute: function(a){ return a==='content' ? "default-src 'none'; script-src 'unsafe-inline';" : null; },
  hasAttribute: function(a){ return a==='content'; },
  tagName: 'META', nodeName: 'META'
});
var __ifDoc;
__ifDoc = __mkObj('iframeDoc', {
  querySelector: function(s){
    if (s && s.indexOf('Content-Security-Policy') !== -1) return __ifMeta;
    if (s === 'meta') return __ifMeta;
    return null;
  },
  querySelectorAll: function(s){
    if (s && s.indexOf('Content-Security-Policy') !== -1) return [__ifMeta];
    if (s === 'meta') return [__ifMeta];
    return [];
  },
  getElementsByTagName: function(t){ return t && t.toLowerCase()==='meta' ? [__ifMeta] : []; },
  body: __mkObj('iframeBody', {
    querySelector: function(s){ return s && s.indexOf('Content-Security-Policy')!==-1 ? __ifMeta : null; },
    querySelectorAll: function(s){ return s && s.indexOf('Content-Security-Policy')!==-1 ? [__ifMeta] : []; },
    appendChild: function(){}, removeChild: function(){}
  }),
  head: __mkObj('iframeHead', {
    querySelector: function(s){ return s && s.indexOf('Content-Security-Policy')!==-1 ? __ifMeta : null; },
    querySelectorAll: function(s){ return s && s.indexOf('Content-Security-Policy')!==-1 ? [__ifMeta] : []; },
    appendChild: function(){}, removeChild: function(){}
  }),
  documentElement: __mkObj('iframeRoot'),
  createElement: function(){ return __mkObj('elem', {setAttribute:function(){}, appendChild:function(){}, removeChild:function(){}, getAttribute:function(){return null;}, hasAttribute:function(){return false;}}); },
  cookie: '', readyState: 'complete'
});

var __iframeEl = __mkObj('iframe', {
  contentDocument: __ifDoc,
  contentWindow: __mkObj('iframeWin', { document: __ifDoc, top: undefined, parent: undefined }),
  document: __ifDoc,
  getAttribute: function(a){
    if (a==='sandbox') return 'allow-scripts allow-same-origin';
    if (a==='srcdoc') return '';
    if (a==='id') return 'jsa';
    return null;
  },
  hasAttribute: function(a){ return a==='sandbox'||a==='id'; },
  tagName: 'IFRAME', nodeName: 'IFRAME', id: 'jsa'
});

var document = __mkObj('document', {
  querySelector: function(s){
    if (s === '#jsa') return __iframeEl;
    if (s && s.indexOf('Content-Security-Policy') !== -1) return __ifMeta;
    return null;
  },
  querySelectorAll: function(s){
    if (s === '#jsa') return [__iframeEl];
    if (s && s.indexOf('Content-Security-Policy') !== -1) return [__ifMeta];
    return [];
  },
  getElementById: function(id){ return id==='jsa' ? __iframeEl : null; },
  getElementsByTagName: function(t){ if(t&&t.toLowerCase()==='iframe') return [__iframeEl]; return []; },
  getElementsByClassName: function(){ return []; },
  body: __mkObj('body', {appendChild:function(){}, removeChild:function(){}, querySelector:function(s){return s==='#jsa'?__iframeEl:null;}, querySelectorAll:function(s){return s==='#jsa'?[__iframeEl]:[];}}),
  head: __mkObj('head', {appendChild:function(){}, removeChild:function(){}, querySelector:function(){return null;}, querySelectorAll:function(){return [];}}),
  documentElement: __mkObj('root'),
  createElement: function(tag){ return __makeHtmlElement(tag||'div'); },
  createTextNode: function(t){ return {nodeType:3, nodeValue:String(t||''), textContent:String(t||'')}; },
  cookie: '', readyState: 'complete', title: '',
  addEventListener: function(){}, removeEventListener: function(){}
});

var window;
window = __mkObj('window', {
  document: document,
  __DDG_BE_VERSION__: 1, __DDG_FE_CHAT_HASH__: 1,
  navigator: __mkObj('navigator', { userAgent: __ua, webdriver: false, language: 'en-US', languages: ['en-US','en'], platform: 'MacIntel', vendor: 'Apple Computer, Inc.', appVersion: '5.0', cookieEnabled: true, onLine: true, hardwareConcurrency: 8, deviceMemory: 8 }),
  innerWidth: 1280, innerHeight: 800, outerWidth: 1280, outerHeight: 800, devicePixelRatio: 1,
  screen: __mkObj('screen', { width:1920, height:1080, availWidth:1920, availHeight:1080, colorDepth:24, pixelDepth:24 }),
  location: __mkObj('location', { href:'https://duckduckgo.com/', origin:'https://duckduckgo.com', host:'duckduckgo.com', hostname:'duckduckgo.com', protocol:'https:', pathname:'/', search:'', hash:'', port:'' }),
  performance: __mkObj('perf', { now: function(){ return 0; }, timeOrigin: 0 }),
  history: __mkObj('history', { length: 1, state: null }),
  localStorage: __mkObj('ls', { getItem:function(){return null;}, setItem:function(){}, removeItem:function(){}, clear:function(){}, length:0, key:function(){return null;} }),
  sessionStorage: __mkObj('ss', { getItem:function(){return null;}, setItem:function(){}, removeItem:function(){}, clear:function(){}, length:0, key:function(){return null;} }),
  addEventListener: function(){}, removeEventListener: function(){}, dispatchEvent: function(){return true;},
  getComputedStyle: function(el){
    var css = (el && el.style && el.style.cssText) || '';
    return {
      getPropertyValue: function(p){
        var m = css.match(new RegExp(p + '\\s*:\\s*([^;]+)', 'i'));
        if (m) return m[1].trim();
        if (p === 'display') return 'block';
        return '';
      },
      display: (css.match(/display\s*:\s*([^;]+)/i)||[])[1]||'block'
    };
  },
  setTimeout: function(fn){ try{fn();}catch(e){} return 0; }, clearTimeout: function(){},
  setInterval: function(){ return 0; }, clearInterval: function(){},
  requestAnimationFrame: function(fn){ try{fn();}catch(e){} return 0; }, cancelAnimationFrame: function(){},
  matchMedia: function(){ return __mkObj('mq', {matches:false, media:'', addListener:function(){}, removeListener:function(){}, addEventListener:function(){}, removeEventListener:function(){}}); },
  hasOwnProperty: function(k){
    if (k==='__DDG_BE_VERSION__'||k==='__DDG_FE_CHAT_HASH__') return true;
    return Object.prototype.hasOwnProperty.call(this,k);
  },
  alert: function(){}, confirm: function(){return true;}, prompt: function(){return '';},
  open: function(){return null;}, close: function(){}, focus: function(){}, blur: function(){}
});
window.top = window; window.self = window; window.window = window; window.parent = window; window.globalThis = window;
var top = window, self = window, parent = window;
var navigator = window.navigator;
var location = window.location;
var screen = window.screen;
var performance = window.performance;
var history = window.history;
var localStorage = window.localStorage;
var sessionStorage = window.sessionStorage;
var getComputedStyle = function(el){ return window.getComputedStyle(el); };
var __R = null, __E = null;
function __HTMLClass(name){ var c = function(){}; c.prototype = __mkObj(name+'.proto'); return c; }
var HTMLElement = __HTMLClass('HTMLElement');
var HTMLDivElement = __HTMLClass('HTMLDivElement');
var HTMLIFrameElement = __HTMLClass('HTMLIFrameElement');
var HTMLDocument = __HTMLClass('HTMLDocument');
var Document = __HTMLClass('Document');
var Element = __HTMLClass('Element');
var Node = __HTMLClass('Node');
var Window = __HTMLClass('Window');
var Event = __HTMLClass('Event');
var MouseEvent = __HTMLClass('MouseEvent');
var KeyboardEvent = __HTMLClass('KeyboardEvent');
var TouchEvent = __HTMLClass('TouchEvent');
var XMLHttpRequest = __HTMLClass('XMLHttpRequest');
var WebSocket = __HTMLClass('WebSocket');
var Image = __HTMLClass('Image');
var FormData = __HTMLClass('FormData');
var Blob = __HTMLClass('Blob');
var File = __HTMLClass('File');
var FileReader = __HTMLClass('FileReader');
var URL = __HTMLClass('URL');
var URLSearchParams = __HTMLClass('URLSearchParams');
var Headers = __HTMLClass('Headers');
var Request = __HTMLClass('Request');
var Response = __HTMLClass('Response');
var fetch = function(){ return Promise.resolve(__mkObj('resp', {ok:true, status:200, json:function(){return Promise.resolve({});}, text:function(){return Promise.resolve('');}})); };
'''

DUCK_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36")
DUCK_FE_VERSION = "serp_20260917_083005_ET-742796f26a61a81dbee67db3e7dd403a0e16294e"
DUCK_SESSION = None
DUCK_WARMED = [False]
DUCK_LOCK = threading.Lock()
DUCK_JWK = [None]


def duck_servers():
    return [
        {"id": "duck-gpt-5.4-mini", "name": "GPT 5.4 Mini (Duck)",
         "model_id": "gpt-5.4-mini", "kind": "duck"},
        {"id": "duck-claude-haiku-4-5", "name": "Claude Haiku 4.5 (Duck)",
         "model_id": "claude-haiku-4-5", "kind": "duck"},
        {"id": "duck-mistral-small", "name": "Mistral Small (Duck)",
         "model_id": "mistral-small-2603", "kind": "duck"},
        {"id": "duck-gpt-oss-120b", "name": "GPT OSS 120B (Duck)",
         "model_id": "tinfoil/gpt-oss-120b", "kind": "duck"},
        {"id": "duck-gemma-4-31b", "name": "Gemma 4 31B (Duck)",
         "model_id": "tinfoil/gemma4-31b", "kind": "duck"},
    ]


def _duck_b64u(b):
    import base64 as _b
    return _b.urlsafe_b64encode(b).decode().rstrip("=")


def _duck_jwk():
    if DUCK_JWK[0] is None:
        from cryptography.hazmat.primitives.asymmetric import rsa
        k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        n = k.public_key().public_numbers().n
        nb = n.to_bytes((n.bit_length() + 7) // 8, "big")
        DUCK_JWK[0] = {"alg": "RSA-OAEP-256", "e": _duck_b64u((65537).to_bytes(3, "big")),
                       "ext": True, "key_ops": ["encrypt"], "kty": "RSA",
                       "n": _duck_b64u(nb), "use": "enc"}
    return DUCK_JWK[0]


def _duck_session():
    global DUCK_SESSION
    if DUCK_SESSION is None:
        DUCK_SESSION = requests.Session()
        DUCK_SESSION.headers.update({
            "User-Agent": DUCK_UA, "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://duck.ai/", "Origin": "https://duck.ai",
            "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"})
    return DUCK_SESSION


def _duck_b64sha(s):
    import base64 as _b, hashlib as _h
    return _b.b64encode(_h.sha256(s.encode("utf-8")).digest()).decode("ascii")


def _duck_solve(challenge_b64):
    """چەلەنجەی JS ی سێرڤەر لە V8 چارە دەکات + wrapper ی FE (origin/stack/duration)"""
    import base64 as _b, json as _j, random as _r
    from py_mini_racer import MiniRacer
    js = _b.b64decode(challenge_b64).decode("utf-8", errors="replace")
    with DUCK_LOCK:
        ctx = MiniRacer()
        try:
            ctx.eval(DUCK_STUBS_JS.replace("__DDG_REAL_UA__", _j.dumps(DUCK_UA))
                                    .replace("__DDG_HTML_LOOKUP__", "{}"))
            ctx.eval("(%s).then(function(v){__R=v;}).catch(function(e){__E=String((e&&e.stack)||e);});" % js)
            for _ in range(100):
                if ctx.execute("__R !== null || __E !== null"):
                    break
                time.sleep(0.02)
            err = ctx.execute("__E")
            if err:
                raise RuntimeError(str(err)[:120])
            res = ctx.execute("__R")
        finally:
            try:
                del ctx
            except Exception:
                pass
    if not isinstance(res, dict) or not res.get("client_hashes"):
        raise RuntimeError("duck: چەلەنجە بەتاڵ")
    ch = list(res["client_hashes"])
    ch[0] = DUCK_UA
    res["client_hashes"] = [_duck_b64sha(x) for x in ch]
    res.setdefault("meta", {})
    res["meta"]["origin"] = "https://duck.ai"
    res["meta"]["stack"] = "Error\n    at https://duck.ai/dist/duckai-dist/entry.duckai.js:2:123456"
    res["meta"]["duration"] = str(_r.randint(40, 250))
    return _b.b64encode(_j.dumps(res, separators=(",", ":")).encode("utf-8")).decode("ascii")


def _duck_signals():
    import base64 as _b, json as _j, random as _r
    now = int(time.time() * 1000)
    t = _r.randint(80, 180)
    ev = [{"name": "onboarding_impression_1", "delta": t}]
    t += _r.randint(120, 260)
    ev.append({"name": "onboarding_impression_2", "delta": t})
    t += _r.randint(200, 500)
    ev.append({"name": "startNewChat", "delta": t})
    for _ in range(_r.randint(6, 14)):
        t += _r.randint(40, 180)
        ev.append({"name": "user_input", "delta": t})
    t += _r.randint(120, 350)
    ev.append({"name": "user_submit", "delta": t})
    p = {"start": now - 8000, "events": ev, "end": t + _r.randint(20, 90)}
    return _b.b64encode(_j.dumps(p, separators=(",", ":")).encode("utf-8")).decode("ascii")


def _duck_warm():
    if DUCK_WARMED[0]:
        return
    with DUCK_LOCK:
        if DUCK_WARMED[0]:
            return
        try:
            _duck_session().get("https://duck.ai/", headers={
                "Accept": "text/html", "Upgrade-Insecure-Requests": "1"}, timeout=(15, 20))
        except Exception:
            pass
        DUCK_WARMED[0] = True


def _duck_attempt(model_id, msgs, timeout):
    import json as _j, random as _r, uuid as _u
    s = _duck_session()
    _duck_warm()
    r = s.get("https://duck.ai/duckchat/v1/status", headers={
        "x-vqd-accept": "1", "Cache-Control": "no-store", "Accept": "*/*"},
        timeout=(15, 25))
    if r.status_code != 200:
        raise EMError(f"duck: status {r.status_code}")
    ch = r.headers.get("x-vqd-hash-1")
    if not ch:
        raise EMError("duck: چەلەنجە نەگەڕایەوە")
    h1 = _duck_solve(ch)
    m = [{"role": x.get("role"), "content": [{"type": "text", "text": x.get("content", "")}]}
         for x in msgs]
    payload = {
        "model": model_id,
        "metadata": {"toolChoice": {"NewsSearch": False, "VideosSearch": False,
                                    "LocalSearch": False, "WeatherForecast": False}},
        "messages": m,
        "canUseTools": False,
        "reasoningEffort": "none",
        "canUseApproxLocation": None,
        "canDelegateImageGeneration": None,
        "canShowGreeting": False,
        "durableStream": {"messageId": str(_u.uuid4()), "conversationId": str(_u.uuid4()),
                          "publicKey": _duck_jwk()},
    }
    hdrs = {"Content-Type": "application/json", "Accept": "text/event-stream",
            "x-vqd-hash-1": h1, "x-fe-signals": _duck_signals(),
            "x-fe-version": DUCK_FE_VERSION, "x-ddg-journey-id": _u.uuid4().hex}
    r2 = s.post("https://duck.ai/duckchat/v1/chat", data=_j.dumps(payload),
                headers=hdrs, timeout=(15, timeout))
    if r2.status_code != 200:
        raise EMError(f"duck: {r2.status_code}")
    text = []
    for line in r2.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        d = line[6:].strip()
        if d == "[DONE]":
            break
        try:
            j = _j.loads(d)
        except Exception:
            continue
        if j.get("action") == "success" and isinstance(j.get("message"), str):
            text.append(j["message"])
        elif j.get("action") == "error":
            raise EMError(f"duck: {str(j.get('type', 'error'))[:50]}")
    ans = "".join(text).strip()
    if not ans:
        raise EMError("duck: وەڵام نەگەڕایەوە")
    return ans


def duck_chat(model_id, messages, timeout=110):
    """چاتی duck.ai — system دەفڕێتە ناو یەکەم نامەی بەکارهێنەر + ٢ هەوڵ"""
    sys_txt = " ".join(m["content"] for m in messages if m.get("role") == "system")[:1200]
    rest = [m for m in messages if m.get("role") != "system"][-21:]
    if rest and rest[0].get("role") == "user" and sys_txt:
        rest[0] = dict(rest[0])
        rest[0]["content"] = f"[ئاراستەی سیستەم: {sys_txt}]\n\n{rest[0]['content']}"
    elif sys_txt:
        rest = [{"role": "user", "content": f"[ئاراستەی سیستەم: {sys_txt}]"}] + rest
    last = None
    for i in range(2):
        try:
            return _duck_attempt(model_id, rest, timeout)
        except EMError as e:
            last = e
            if "418" not in str(e) and "429" not in str(e):
                raise
            time.sleep(1.5 + i)
    raise last or EMError("duck: شکست")



# ════════════════════════════════════════════════════════════
# ٢.١٤) anakin.ai — «Free No Sign Up Chatgpt» — Gemini بێ تۆمار
#      node client (anakin_client.mjs) — واژووی ڕەسەن: md5(object-hash(body)+SECRET+ts)
#      لیمیت: ~٢ نامە/IP/پەنجەرە → cooldown ١٠ خولەک دوای ٤٢٩ — فەڵباکی زنجیرە
# ════════════════════════════════════════════════════════════

AK_CLIENT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anakin_client.mjs")
_AK_COOLDOWN = {"until": 0.0}


def ak_servers():
    return [
        {"id": "ak-gemini-2.5-flash", "name": "Gemini 2.5 Flash (Anakin)",
         "model_id": "308", "kind": "ak"},
        {"id": "ak-gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite (Anakin)",
         "model_id": "309", "kind": "ak"},
    ]


def ak_chat(model_id, messages, timeout=110):
    """چاتی anakin — node client؛ system تێکەڵ بە یەکەم نامە (شێوازی qb)"""
    import time as _t
    if _t.time() < _AK_COOLDOWN["until"]:
        raise EMError("ak: cooldown")
    sys_txt = " ".join(m["content"] for m in messages if m.get("role") == "system")[:1200]
    rest = [m for m in messages if m.get("role") in ("user", "assistant")][-21:]
    if rest and rest[0].get("role") == "user" and sys_txt:
        rest = [dict(rest[0])]
        rest[0] = dict(rest[0])
        rest[0]["content"] = f"[ئاراستەی سیستەم: {sys_txt}]\n\n{rest[0]['content']}"
    payload = json.dumps({"model_id": int(model_id), "messages": rest}, ensure_ascii=False)
    try:
        p = subprocess.run([NODE_BIN, AK_CLIENT], input=payload.encode("utf-8"),
                           capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise EMError("ak: timeout")
    lines = [l for l in (p.stdout or b"").decode("utf-8", "replace").strip().splitlines() if l.strip()]
    if not lines:
        raise EMError("ak: no output")
    try:
        obj = json.loads(lines[-1])
    except Exception:
        raise EMError("ak: bad output")
    if obj.get("ok") and obj.get("answer"):
        return obj["answer"]
    code = str(obj.get("code") or "")
    if "429" in code:
        _AK_COOLDOWN["until"] = _t.time() + 600
    raise EMError(obj.get("error") or "ak: failed", obj.get("code"))



# ════════════════════════════════════════════════════════════
# ٢.١٥) notegpt.io — AI Answer Generator — Gemini بێ تۆمار
#      POST /api/v2/homework/stream (SSE: data:{"text":...}) — بێ چەلەنجە، بێ کوکی
#      flash-lite: کراوە (~٩ نامە/IP/ڕۆژ) — pro: لیمیت ڕۆژانەی توند (٤٢٩٠١٦)
# ════════════════════════════════════════════════════════════

NG_LIMIT = {"until": 0.0}


# ══════════ LLM7 (llm7.io) — بێ کلیل، OpenAI-سازگار §2.17 ══════════
L7_LIMIT = {"until": 0.0}
L7_BASE = "https://api.llm7.io/v1"
L7_FALLBACK = [("codestral-latest", "Codestral"),
               ("mistral-Nemo-Instruct-2407", "Mistral Nemo"),
               ("minimax-m2.7", "MiniMax M2.7"),
               ("GLM-5.3-Flash", "GLM 5.3 Flash")]


def sync_l7_models():
    """ئۆتۆ-سینکی llm7 — turbo ی کۆمەڵگە + پشکنینی نوێیەکان (٣ لە خولێکدا) — هەر ٣٠ خولەک"""
    import time as _t
    if _t.time() - MS_T["l7"] < 1800:
        return
    try:
        r = requests.get(L7_BASE + "/models", headers={"User-Agent": ACT_UAS[0]},
                         timeout=(10, 20))
        items = (r.json() or {}).get("data") or []
    except Exception:
        return
    MS_T["l7"] = _t.time()
    cands = [m["id"] for m in items
             if m.get("tier") == "turbo" and m.get("model_type", "chat") == "chat"]
    # تێبینی: ok تەنها کاتێک لابردرێت کە چاتەکەی خۆی شکست بخوات (ل7 catalogs بەپێی ناوچە دەگۆڕدرێت)
    # bad ی کۆن دووبارە تاقی بکەوە (٢٤ کاتژمێر)
    for mid in list(MS["l7_bad"].keys()):
        if _t.time() - float(MS["l7_bad"][mid].get("t") or 0) > 86400:
            del MS["l7_bad"][mid]
    probed = 0
    for mid in cands:
        if mid in MS["l7_ok"] or mid in MS["l7_bad"] or probed >= 3:
            continue
        probed += 1
        try:
            rr = requests.post(L7_BASE + "/chat/completions",
                               json={"model": mid, "messages": [{"role": "user", "content": "Reply with: OK"}],
                                     "max_tokens": 8},
                               headers={"User-Agent": ACT_UAS[0], "Content-Type": "application/json"},
                               timeout=(10, 45))
            if rr.status_code == 200 and (rr.json().get("choices") or [{}])[0].get("message", {}).get("content"):
                MS["l7_ok"][mid] = {"t": _t.time()}
                print(f"[SYNC] l7: نوێی بێ-کلیل ✅ {mid}", flush=True)
            else:
                MS["l7_bad"][mid] = {"code": rr.status_code, "t": _t.time()}
        except Exception as e:
            MS["l7_bad"][mid] = {"err": str(e)[:60], "t": _t.time()}
        _ms_save()
        _t.sleep(1.5)


def l7_servers():
    ids = list(MS["l7_ok"].keys())
    if not ids:
        ids = [f for f, _ in L7_FALLBACK]
    labels = dict(L7_FALLBACK)
    out = []
    for mid in ids[:8]:
        label = labels.get(mid, (mid.split("-")[0].capitalize() if mid else "LLM7"))
        slug = re.sub(r'[^a-z0-9.]+', '-', mid.lower()).strip('-')
        out.append({"id": f"l7-{slug}", "name": f"{label} (LLM7)",
                    "model_id": mid, "kind": "l7"})
    return out


def l7_chat(messages, model_id="mistral-Nemo-Instruct-2407", timeout=90):
    """چاتی llm7.io — میوان: ١٠ داواکاری/خولەک، ٦٠/کاتژمێر بێ کلیل"""
    import time as _t
    if _t.time() < L7_LIMIT["until"]:
        raise EMError("l7: cooldown")
    body = {"model": model_id, "messages": messages, "max_tokens": 1400}
    try:
        r = requests.post(L7_BASE + "/chat/completions", json=body,
                          headers={"User-Agent": ACT_UAS[random.randrange(len(ACT_UAS))],
                                   "Content-Type": "application/json",
                                   "Referer": "https://llm7.io"},
                          timeout=(15, timeout))
    except Exception as e:
        raise EMError(f"l7: {str(e)[:60]}")
    if r.status_code != 200:
        if r.status_code in (429, 402):
            L7_LIMIT["until"] = _t.time() + 600
        elif r.status_code in (400, 401, 404) and model_id in MS.get("l7_ok", {}):
            # مۆدێڵ لە ترافیکی ڕاستەقینەدا مردووە (نەک ڕێگری کاتی) — لە ok بۆ bad بیبە (٢٤ کاتژمێر دووبارە)
            MS["l7_ok"].pop(model_id, None)
            MS.setdefault("l7_bad", {})[model_id] = {"code": r.status_code, "t": _t.time()}
            _ms_save()
            print(f"[L7] مردوو لە چاتی ڕاستەقینە: {model_id} ({r.status_code}) — لە ok لابرا", flush=True)
        raise EMError(f"l7: {r.status_code}")
    try:
        m = r.json()["choices"][0]["message"]
    except Exception:
        raise EMError("l7: parse")
    return (m.get("content") or "").strip()


# ══════════ G4F Space (g4f.space) — کریتی PoW §2.18 ══════════
G4F_LIMIT = {"until": 0.0}
G4F_BASE = "https://g4f.space"
_G4F_CREDIT = {"v": 0}
_G4F_BAKE_LOCK = threading.Lock()


def _g4f_headers():
    return {"User-Agent": ACT_UAS[random.randrange(len(ACT_UAS))],
            "Content-Type": "application/json",
            "Referer": "https://g4f.dev/"}


def _cake_pow(uuid, salt, difficulty, max_nonce=120_000_000):
    """PoW: sha256(uuid:salt:nonce) ≥ difficulty بتی سیفر لە سەرەتا"""
    import hashlib as _hl
    pre = f"{uuid}:{salt}:".encode()
    thr = (1 << (32 - difficulty)) if 0 < difficulty < 32 else 1
    n = 0
    digest = _hl.sha256
    while n < max_nonce:
        end = n + 200000
        for nn in range(n, end):
            d = digest(pre + str(nn).encode()).digest()
            if int.from_bytes(d[:4], "big") < thr:
                return nn, d.hex()
        n = end
    return None, None


def _g4f_status():
    r = requests.get(G4F_BASE + "/cake/status", headers=_g4f_headers(), timeout=(10, 15))
    return r.json() if r.status_code == 200 else {}


def _g4f_bake_one(uuid, difficulty):
    nonce, hx = _cake_pow(uuid, "0", difficulty)
    if not nonce:
        return 0
    try:
        rb = requests.post(G4F_BASE + "/cake/bake", headers=_g4f_headers(),
                           json={"uuid": uuid, "salt": "0", "nonce": nonce, "hash": hx},
                           timeout=(10, 20))
        if rb.status_code == 200:
            j = rb.json() or {}
            return int(j.get("total_credit_cents") or j.get("credit_cents") or 0)
    except Exception:
        pass
    return 0


def _g4f_ensure_credits(min_credits=6, bake_max=2):
    """کەیک بنێژە ئەگەر کریت کەمە (١ کەیک = ٥ کریت، ~٥-١٥ چرکە)"""
    with _G4F_BAKE_LOCK:
        try:
            st = _g4f_status()
        except Exception:
            return
        _G4F_CREDIT["v"] = int(st.get("credit_cents") or 0)
        if _G4F_CREDIT["v"] >= min_credits:
            return
        diff = int(st.get("difficulty") or 24)
        try:
            r = requests.get(G4F_BASE + "/cake/issue?n=" + str(bake_max),
                             headers=_g4f_headers(), timeout=(10, 15))
            uuids = (r.json() or {}).get("uuids") or []
        except Exception:
            return
        for uuid in uuids:
            tot = _g4f_bake_one(uuid, diff)
            if tot:
                _G4F_CREDIT["v"] = tot
            time.sleep(0.3)
            if _G4F_CREDIT["v"] >= min_credits:
                break


def _g4f_baker_daemon():
    """پاشبنەما: کریت ≥ ١٠ ڕابگرێت (١٠٠ کەیک/ڕۆژ بۆ هەر IP)"""
    time.sleep(20)
    while True:
        try:
            st = _g4f_status()
            if int(st.get("credit_cents") or 0) < 10 and int(st.get("baked_today") or 0) < int(st.get("limit_per_day") or 100):
                _g4f_ensure_credits(min_credits=12, bake_max=3)
        except Exception:
            pass
        time.sleep(90)


G4F_TRUST = {"groq.com", "nvidia.com", "gemini-v1beta", "ollama.com", "ollama-swarm",
             "ollama.pro", "logfare.ai", "relayrouter.org", "openrouter.ai"}
G4F_EXCLUDE = ("whisper", "tts", "embed", "bge", "guard", "image", "flux",
               "stable-diffusion", "sdxl", "music", "video", "dall")


def _g4f_models():
    """داینامیکی تەواو — باشترین ٨ بە باوبانگ لە پڕۆڤایەری متمانەپێکراو"""
    out, seen = [], set()
    try:
        r = requests.get(G4F_BASE + "/v1/models", headers=_g4f_headers(), timeout=(10, 20))
        items = (r.json() or {}).get("data") or []
    except Exception:
        items = []
    PREFER = ["openai/gpt-oss-120b", "gpt-4o-mini"]
    # ١. دوو دڵنیاکە
    for tail in PREFER:
        for it in items:
            sid = str(it.get("id") or "")
            if sid == tail or sid.endswith(":" + tail):
                slug = re.sub(r"[^a-z0-9.]+", "-", tail.lower()).strip("-")
                if slug not in seen:
                    seen.add(slug)
                    out.append({"id": f"g4f-{slug}", "name": f"{tail.split('/')[-1]} (G4F)",
                                "model_id": sid, "kind": "g4f"})
                break
    # ٢. پڕۆڤایەری متمانەپێکراو — ڕیز بە داواکاری
    pool = []
    for it in items:
        sid = str(it.get("id") or "")
        owner = str(it.get("owned_by") or "")
        if owner not in G4F_TRUST:
            continue
        if owner == "openrouter.ai" and ":free" not in sid:
            continue
        base = sid.split(":", 1)[1] if ":" in sid else sid
        low = base.lower()
        if any(x in low for x in G4F_EXCLUDE):
            continue
        try:
            reqs = int(it.get("requests") or 0)
        except Exception:
            reqs = 0
        pool.append((reqs, base, sid))
    pool.sort(reverse=True)
    for reqs, base, sid in pool:
        if len(out) >= 8:
            break
        slug = re.sub(r"[^a-z0-9.]+", "-", base.lower()).strip("-")
        if slug in seen:
            continue
        seen.add(slug)
        out.append({"id": f"g4f-{slug}", "name": f"{base} (G4F)", "model_id": sid, "kind": "g4f"})
    return out


def g4f_chat(messages, model_id, timeout=110):
    """چاتی g4f.space — کریتی PoW؛ ٤٠٢/٤٢٩ → ١٥ خولەک cooldown"""
    import time as _t
    if _t.time() < G4F_LIMIT["until"]:
        raise EMError("g4f: cooldown")
    if _G4F_CREDIT["v"] < 4:
        _g4f_ensure_credits(min_credits=4, bake_max=1)
    try:
        r = requests.post(G4F_BASE + "/v1/chat/completions",
                          json={"model": model_id, "messages": messages},
                          headers=_g4f_headers(), timeout=(15, timeout))
    except Exception as e:
        raise EMError(f"g4f: {str(e)[:60]}")
    if r.status_code != 200:
        if r.status_code in (402, 429):
            G4F_LIMIT["until"] = _t.time() + 900
        raise EMError(f"g4f: {r.status_code}")
    try:
        return (r.json()["choices"][0]["message"].get("content") or "").strip()
    except Exception:
        raise EMError("g4f: parse")


def ng_servers():
    return [{"id": "ng-gemini-flash-lite", "name": "Gemini 3.1 Flash Lite (NoteGPT)",
             "model_id": "gemini-3.1-flash-lite", "kind": "ng"}]


def ng_chat(messages, timeout=110):
    """چاتی notegpt — مێژوو بۆ یەک نامە؛ template ی homework یش لابردن"""
    import time as _t
    if _t.time() < NG_LIMIT["until"]:
        raise EMError("ng: cooldown")
    sys_txt = " ".join(m["content"] for m in messages if m.get("role") == "system")[:1000]
    user_txt = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_txt = m["content"]
            break
    if not user_txt:
        user_txt = " ".join(m.get("content", "") for m in messages)[-2000:]
    if sys_txt:
        user_txt = f"[ئاراستەی سیستەم: {sys_txt}]\n\n{user_txt}"
    try:
        r = requests.post("https://notegpt.io/api/v2/homework/stream",
                          json={"message": user_txt, "language": "auto", "model": "gemini-3.1-flash-lite",
                                "tone": "default", "length": "moderate",
                                "conversation_id": str(__import__("uuid").uuid4())},
                          headers={"User-Agent": ACT_UAS[random.randrange(len(ACT_UAS))],
                                   "Origin": "https://notegpt.io",
                                   "Referer": "https://notegpt.io/ai-answer-generator"},
                          timeout=(15, timeout), stream=True)
    except Exception as e:
        raise EMError(f"ng: {str(e)[:60]}")
    if r.status_code != 200:
        if r.status_code == 429:
            NG_LIMIT["until"] = _t.time() + 1800
        raise EMError(f"ng: {r.status_code}")
    text = []
    limit_hit = False
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        try:
            d = json.loads(line[6:])
        except Exception:
            continue
        if isinstance(d.get("text"), str):
            text.append(d["text"])
        if d.get("code") == 164016:
            limit_hit = True
    ans = "".join(text).strip()
    if limit_hit and not ans:
        NG_LIMIT["until"] = _t.time() + 1800
        raise EMError("ng: لیمیت ڕۆژانە")
    # template ی homework پاک بکەوە
    ans = re.sub(r"^###\s*Question\s*\d*\s*", "", ans)
    ans = re.sub(r"\n?###\s*(Answer|Solution Steps|[^\n]*)\s*", "\n", ans)
    ans = ans.strip()
    if ans:
        return ans
    raise EMError("ng: وەڵام نەگەڕایەوە")



# ════════════════════════════════════════════════════════════
# ٢.١٦) ئۆتۆ-سینکی مۆدێڵ — ئەگەر سەرچاوەیەک مۆدێڵی نوێ زیاد بکات یان بگۆڕێت
#      خۆکارانە دەخوێنرێتەوە؛ تەنها مۆدێڵی ڕاییگەی سەلمێنراو زیاد دەکرێت
#      duck: لیست لە bundle ی فەرمییەوە | ak: پڕۆب ی بچووک بۆ مۆدێڵی نوێ
# ════════════════════════════════════════════════════════════

MODEL_SYNC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_sync.json")
MS = {"duck": {}, "ak_ok": {}, "ak_block": {}, "l7_ok": {}, "l7_bad": {}, "ct_ok": {}, "ct_bad": {}, "yl_ok": {}, "yl_bad": {}, "hk_ok": {}, "hk_bad": {}, "hf_ok": {}, "hf_bad": {}, "aka_ok": {}, "aka_bad": {}, "hb_ok": {}, "hb_bad": {}, "gk_ok": {}, "gk_bad": {}, "gz_ok": {}, "gz_bad": {}, "pi_ok": {}, "pi_bad": {}, "cb_ok": {}, "cb_bad": {}, "nv_ok": {}, "nv_bad": {}, "al_ok": {}, "al_bad": {}, "aiml_ok": {}}
MS_T = {"duck": 0.0, "ak": 0.0, "l7": 0.0, "ct": 0.0, "yl": 0.0, "hk": 0.0, "hf": 0.0, "aka": 0.0, "hb": 0.0, "gk": 0.0, "gz": 0.0, "pi": 0.0, "cb": 0.0, "ac": 0.0, "nv": 0.0, "al": 0.0}
MS_LOCK = threading.Lock()


def _ms_load():
    try:
        with open(MODEL_SYNC_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        for k in ("duck", "ak_ok", "ak_block", "l7_ok", "l7_bad", "ct_ok", "ct_bad", "yl_ok", "yl_bad", "hk_ok", "hk_bad", "hf_ok", "hf_bad", "aka_ok", "aka_bad", "hb_ok", "hb_bad", "gk_ok", "gk_bad", "gz_ok", "gz_bad", "pi_ok", "pi_bad", "cb_ok", "cb_bad", "nv_ok", "nv_bad", "al_ok", "al_bad", "aiml_ok"):
            v = d.get(k)
            if isinstance(v, dict):
                MS[k].update(v)
    except Exception:
        pass


def _ms_save():
    try:
        with open(MODEL_SYNC_FILE, "w", encoding="utf-8") as f:
            json.dump(MS, f, ensure_ascii=False)
    except Exception:
        pass


_ms_load()


# ══════════ ChatTide (chattide.ai) — §2.20 — ٢ چات/ڕۆژ بۆ هەر IP (٠٠:٠٠ UTC نوێ دەبێتەوە) ══════════
CT_LIMIT = {"quota_until": 0.0, "wobble_until": 0.0}
CT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
_CT_N = int(
    "c201d7ff13221b2c1c631aa9a1eea2d4ebf08f0b3aeefbbe7ef363923d9fa77f8045be0f3c76ba59e8a8a0356d09f13360c5ee989acd62ac264d543caef915ec978cbfedcd8a3877383864f31c1e5f50c88c6ac154bdc12cd8fef47bac80fec28765f04b1b55cf8656fce086ecde7843dd6e5ed92b82fb812e5646aaccdd3c2d", 16)
_CT_E = 65537
_CT_SYNC = {"t": 0.0}
_CT_ARR_RE = re.compile(r'\[\{name:"[^"]{1,50}",value:"[^"]{1,50}"\}(?:,\{name:"[^"]{1,50}",value:"[^"]{1,50}"\}){0,30}\]')
_CT_VAL_RE = re.compile(r'\{name:"([^"]{1,50})",value:"([^"]{1,50})"\}')
_CT_FALLBACK = [("gpt-5.6-luna", "GPT 5.6 Luna")]


def _ct_vtoken(vid):
    """vtoken = base64(RSA-PKCS1v15-pub(vid)) — تەنها stdlib (پادینی تایپ-٢ ڕاندۆم)"""
    import base64 as _b64
    import secrets as _sc
    ps_len = 128 - 3 - len(vid)
    ps = bytearray()
    while len(ps) < ps_len:
        b = _sc.token_bytes(1)
        if b != b"\x00":
            ps += b
    em = b"\x00\x02" + bytes(ps) + b"\x00" + vid.encode()
    return _b64.b64encode(pow(int.from_bytes(em, "big"), _CT_E, _CT_N).to_bytes(128, "big")).decode()


def _ct_identity():
    """ناسنامەی میوانی نوێ: visitorId = md5-ڕاندۆم → vtoken + mo_uuid"""
    import hashlib as _hl
    from urllib.parse import quote as _q
    vid = _hl.md5(("ct" + str(time.time_ns()) + str(random.random())).encode()).hexdigest()
    vt = _ct_vtoken(vid)
    mo = _hl.md5(("mo" + vid).encode()).hexdigest()
    hd = {"accept": "text/event-stream,application/json, text/event-stream",
          "content-type": "application/json", "lang": "en", "source": "web",
          "referer": "https://www.chattide.ai/", "origin": "https://www.chattide.ai",
          "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="153", "HeadlessChrome";v="153"',
          "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
          "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site",
          "user-agent": CT_UA, "vtoken": vt}
    ck = {"NEXT_LOCALE": "en", "mo_uuid": mo, "chatTide.visitor.id": _q(vt, safe="")}
    return hd, ck


def _ct_quota_ts():
    """نیوەشەوی UTC ی داهاتوو + ٥ خولەک — کاتی نوێبوونەوەی کوانتای ڕۆژانە"""
    return (int(time.time()) // 86400 + 1) * 86400 + 300


def ct_chat(messages, model_id="gpt-5.6-luna", timeout=150):
    """چاتی chattide.ai — میوان: ٢ چات/ڕۆژ بۆ هەر IP؛ کۆدی 229 → دیلی تا نیوەشەوی UTC"""
    import time as _t
    if _t.time() < CT_LIMIT["quota_until"]:
        raise EMError("ct: daily quota (2/IP/day)")
    if _t.time() < CT_LIMIT["wobble_until"]:
        raise EMError("ct: wobble cooldown")
    hd, ck = _ct_identity()
    body = {"spaceHandle": True, "roleId": 0, "conversationId": None, "model": model_id,
            "messages": [{"role": m.get("role", "user"),
                          "content": [{"type": "text", "text": m.get("content") or ""}]} for m in messages]}
    try:
        r = requests.post("https://api.chattide.ai/aigc/chat/v2/professional/stream",
                          json=body, headers=hd, cookies=ck, timeout=(15, timeout))
    except Exception as e:
        raise EMError(f"ct: {str(e)[:60]}")
    if r.status_code != 200:
        raise EMError(f"ct: {r.status_code}")
    txt = r.text
    if '"code":229' in txt or "quota has been exhausted" in txt:
        CT_LIMIT["quota_until"] = _ct_quota_ts()
        raise EMError("ct: 229 quota → دیلی بۆ نیوەشەوی UTC")
    out = []
    for line in txt.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        tok = line[5:].strip()
        if not tok or tok == "--@DONE@--":
            continue
        if tok.startswith("Please refresh"):
            CT_LIMIT["wobble_until"] = _t.time() + 600
            raise EMError("ct: refresh-wobble → دیلی ١٠ خولەک")
        if tok.startswith("{"):
            try:
                j = json.loads(tok)
            except Exception:
                continue
            if str(j.get("code")) == "229" or "quota" in str(j.get("message") or "").lower():
                CT_LIMIT["quota_until"] = _ct_quota_ts()
                raise EMError("ct: 229 quota → دیلی بۆ نیوەشەوی UTC")
            continue
        out.append(tok)
    ans = "".join(out).replace("-=- --", " ").replace("-=-n--", "\n").strip()
    ans = re.sub(r" {3,}", "  ", ans)
    if not ans:
        CT_LIMIT["wobble_until"] = _t.time() + 300
        raise EMError("ct: وەڵام بەتاڵ")
    CT_LIMIT["quota_until"] = 0.0
    CT_LIMIT["wobble_until"] = 0.0
    return ans


def _ct_label(mid):
    out = []
    for p in str(mid).split("-"):
        out.append(p if p and p[0].isdigit() else p.capitalize())
    return " ".join(out)


def ct_servers():
    ids = list(MS.get("ct_ok", {}).keys()) or [f for f, _ in _CT_FALLBACK]
    labels = dict(_CT_FALLBACK)
    out = []
    for mid in ids[:6]:
        label = labels.get(mid, _ct_label(mid))
        slug = re.sub(r'[^a-z0-9.]+', '-', str(mid).lower()).strip('-')
        out.append({"id": f"ct-{slug}", "name": f"{label} (ChatTide)",
                    "model_id": mid, "kind": "ct"})
    return out


def _ct_is_model(val):
    v = str(val)
    if not re.match(r'^(gpt|claude|gemini|grok|llama|qwen|deepseek|mistral|glm|kimi|minimax|o[1-9])[\w.\-]*$', v):
        return False
    return not any(w in v for w in ("whisper", "tts", "embed", "image", "flux", "video", "music", "guard"))


def sync_ct_models(force=False):
    """ئۆتۆ-ئەپدێتی chattide: لیستی مۆدێڵە زیندووەکان لە چەرەکەکانی Next.js (TTL ٦ کاتژمێر).
       هیچ شتێک ناسڕدرێتەوە — تەنها زیادکردن (یاسای ڕاگرتنی هەموو مۆدێڵەکان)"""
    import time as _t
    if not force and _t.time() - _CT_SYNC["t"] < 21600:
        return
    _CT_SYNC["t"] = _t.time()
    found = {}

    def _scan(js):
        if 'value:"' not in js:
            return
        for arr in _CT_ARR_RE.findall(js):
            for _nm, val in _CT_VAL_RE.findall(arr):
                if _ct_is_model(val):
                    found[val] = True

    try:
        h = {"User-Agent": CT_UA}
        html = requests.get("https://www.chattide.ai/chat/", headers=h, timeout=(10, 20)).text
        chunks = set(re.findall(r'/_next/static/chunks/[a-zA-Z0-9/_.\-]+\.js', html))
        for cu in list(chunks)[:6]:
            try:
                js = requests.get("https://www.chattide.ai" + cu, headers=h, timeout=(10, 15)).text
                _scan(js)
                chunks |= set(re.findall(r'/_next/static/chunks/[a-zA-Z0-9/_.\-]+\.js', js))
            except Exception:
                continue
        for cu in list(chunks)[:30]:
            try:
                js = requests.get("https://www.chattide.ai" + cu, headers=h, timeout=(10, 15)).text
            except Exception:
                continue
            _scan(js)
    except Exception as e:
        print(f"[CT-SYNC] هەڵە: {str(e)[:80]}", flush=True)
        return
    added = 0
    for mid in found:
        if mid not in MS.get("ct_ok", {}) and mid not in MS.get("ct_bad", {}):
            MS.setdefault("ct_ok", {})[mid] = {"t": time.time()}
            added += 1
            print(f"[CT-SYNC] مۆدێڵی نوێ: {mid}", flush=True)
    if added:
        _ms_save()
    print(f"[CT-SYNC] chattide: {len(found)} دۆزرا، {added} زیادکرا، ct_ok={len(MS.get('ct_ok', {}))}", flush=True)


# ══════════ Yollo AI (yollo.ai) — §2.21 — بێ لیمیت بۆ دەق (پارە لە وێنە/ڤیدیۆ) ══════════
YL_BASE = "https://www.yollo.ai"
YL_BOT = 147747
YL_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
_YL = {"tok": "", "sid": "", "finger": "", "t": 0.0}


def _yl_headers(finger, tok=None, ct=True):
    hd = {"User-Agent": YL_UA, "x-platform": "web", "x-version": "999.0.0",
          "x-finger": finger, "x-language": "en", "Origin": YL_BASE,
          "Referer": YL_BASE + "/ar/chat"}
    if ct:
        hd["Content-Type"] = "application/json"
    if tok:
        hd["x-auth-token"] = tok
    return hd


def _yl_identity(force=False):
    """میوانی نوێ: createGuest → loginByGuest (JWT ٣٠ ڕۆژ) → createSession — بێ captcha"""
    import time as _t
    import hashlib as _hl
    if not force and _YL["tok"] and _YL["sid"] and _t.time() - _YL["t"] < 4 * 86400:
        return
    finger = _hl.md5(("yl" + str(_t.time_ns()) + str(random.random())).encode()).hexdigest()
    g = requests.post(YL_BASE + "/api/auth/createGuest", headers=_yl_headers(finger, ct=False), timeout=(10, 20)).json()
    d = g.get("data") or {}
    if not d.get("guestUid"):
        raise EMError(f"yl: createGuest {str(g)[:60]}")
    r2 = requests.post(YL_BASE + "/api/auth/loginByGuest", headers=_yl_headers(finger), json=d, timeout=(10, 20)).json()
    tok = (r2.get("data") or {}).get("idToken")
    if not tok:
        raise EMError(f"yl: login {str(r2)[:60]}")
    r3 = requests.post(YL_BASE + "/api/msg/createSession", params={"botId": YL_BOT},
                       headers=_yl_headers(finger, tok=tok, ct=False), timeout=(10, 20)).json()
    sid = (r3.get("data") or {}).get("id")
    if not sid:
        raise EMError(f"yl: session {str(r3)[:60]}")
    _YL.update(tok=tok, sid=str(sid), finger=finger, t=_t.time())


def yl_chat(messages, model_id="yollo-chat", timeout=120):
    """چاتی yollo.ai — مێژوو لە کلایەنتەوە (سیستەم-پرۆمپتی خۆمان) — دەق بێ لیمیت"""
    import time as _t
    if not messages:
        raise EMError("yl: هیچ نامە")
    last = ""
    for m in reversed(messages):
        if m.get("role") == "user" and m.get("content"):
            last = m["content"]
            break
    if not last:
        last = messages[-1].get("content") or ""
    hist = [{"role": m.get("role", "user"), "content": m.get("content") or ""}
            for m in messages if m.get("content")]
    if hist and hist[-1]["role"] == "user" and hist[-1]["content"] == last:
        hist = hist[:-1]
    lasterr = None
    for attempt in range(2):
        try:
            _yl_identity(force=(attempt == 1))
        except Exception as e:
            lasterr = e
            continue
        body = {"message": last, "sessionId": _YL["sid"], "conversationHistory": hist[-21:],
                "userToken": _YL["tok"], "userLocale": "en", "isRegenerate": False,
                "isSafeMode": False, "generateType": 0}
        try:
            r = requests.post(YL_BASE + "/chat-stream", json=body,
                              headers=_yl_headers(_YL["finger"]), timeout=(15, timeout), stream=True)
        except Exception as e:
            lasterr = EMError(f"yl: {str(e)[:60]}")
            continue
        if r.status_code != 200:
            lasterr = EMError(f"yl: {r.status_code}")
            _YL["tok"] = ""
            continue
        out = []
        bad = None
        for line in r.text.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            p = line[5:].strip()
            if not p:
                continue
            try:
                j = json.loads(p)
            except Exception:
                continue
            ty = j.get("type")
            if ty == "content":
                out.append(j.get("content") or "")
            elif ty == "end":
                break
            elif ty in ("error", "errorMsg") or j.get("error") or "error" in str(ty or "").lower():
                bad = str(j.get("message") or j)[:80]
                break
        ans = "".join(out).strip()
        if ans:
            return ans
        lasterr = EMError(f"yl: {bad or 'وەڵام بەتاڵ'}")
        _YL["sid"] = ""
    raise lasterr or EMError("yl: شکست")


def yl_servers():
    out = []
    for mid in list(MS.get("yl_ok", {}).keys())[:3] or ["yollo-chat"]:
        out.append({"id": "yl-yollo-chat", "name": "Yollo Chat",
                    "model_id": mid, "kind": "yl"})
    return out


def sync_yl_models(force=False):
    """ئۆتۆ-ئەپدێتی yollo: پشکنینی زیندووی فلۆوی میوان (٦ کاتژمێر) — مۆدێڵی چات لە سێرڤەرەوە شاراوەیە"""
    import time as _t
    if not force and _t.time() - MS_T.get("yl", 0.0) < 21600:
        return
    MS_T["yl"] = _t.time()
    try:
        r = requests.get(YL_BASE + f"/api/bot?botId={YL_BOT}",
                         headers={"User-Agent": YL_UA}, timeout=(10, 20))
        if r.status_code != 200:
            print(f"[YL-SYNC] بۆت ڕێک نەگەیشت: {r.status_code}", flush=True)
            return
        MS.setdefault("yl_ok", {})["yollo-chat"] = {"t": _t.time()}
        _ms_save()
        print("[YL-SYNC] yollo زیندووە — yollo-chat ئامادە", flush=True)
    except Exception as e:
        print(f"[YL-SYNC] هەڵە: {str(e)[:80]}", flush=True)


# ══════════ Heck AI (heck.ai) — §2.22 — بێ لۆگین؛ FREE = ٥٠ چات/ڕۆژ؛ probe-gated ══════════
HK_BASE = "https://api.heckai.weight-wave.com/api/ha/v1"
HK_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
HK_LIMIT = {"until": 0.0}
_HK = {"sid": "", "t": 0.0}
# کاتالۆگی تایر-فری (لە چەرەکی layout هەڵدرا) — premium ەکان 401 ن — دانەمەزرێن
HK_CATALOG = [
    ("deepseek/deepseek-v4-flash", "DeepSeek v4 Flash"),
    ("deepseek/deepseek-v4-pro", "DeepSeek v4 Pro"),
    ("tencent/hy3-preview", "Tencent Hy3 Preview"),
    ("qwen/qwen3.7-plus", "Qwen 3.7 Plus"),
    ("stepfun/step-3.7-flash", "Step 3.7 Flash"),
    ("google/gemini-3.1-flash-lite", "Gemini 3.1 Flash Lite"),
    ("google/gemini-3-flash-preview", "Gemini 3.0 Flash"),
    ("openai/gpt-5.4-mini", "GPT 5.4 mini"),
    ("minimax/minimax-m3", "Minimax M3"),
    ("anthropic/claude-opus-4.8", "Claude Opus 4.8"),
]


def _hk_headers():
    return {"User-Agent": HK_UA, "Content-Type": "application/json",
            "Origin": "https://heck.ai", "Referer": "https://heck.ai/", "authorization": ""}


def _hk_session(force=False):
    import time as _t
    if not force and _HK["sid"] and _t.time() - _HK["t"] < 3600:
        return _HK["sid"]
    r = requests.post(HK_BASE + "/session/create", json={"title": "chat"},
                      headers=_hk_headers(), timeout=(10, 20))
    sid = (r.json() or {}).get("id")
    if not sid:
        raise EMError(f"hk: session {str(r.text)[:60]}")
    _HK.update(sid=sid, t=_t.time())
    return sid


def _hk_quota_ts():
    import time as _t
    return (int(_t.time()) // 86400 + 1) * 86400 + 300


def hk_chat(messages, model_id="deepseek/deepseek-v4-flash", timeout=120):
    """چاتی heck.ai — تک-شۆت (پرسیار + وەڵامی پێشوو)؛ 402 = کرێکی OpenRouter ەکەیان"""
    import time as _t
    if _t.time() < HK_LIMIT["until"]:
        raise EMError("hk: upstream credit cooldown")
    last, pq, pa = "", None, None
    for m in reversed(messages):
        c = (m.get("content") or "").strip()
        if not c:
            continue
        if m.get("role") == "user":
            last = c
            break
        if pa is None:
            pa = c
        elif pq is None:
            pq = c
    if not last:
        raise EMError("hk: هیچ پرسیار")
    sid = _hk_session()
    body = {"model": model_id, "question": last[-4000:], "language": "English",
            "sessionId": sid, "previousQuestion": pq, "previousAnswer": pa,
            "imgUrls": [], "superSmartMode": False}
    try:
        r = requests.post(HK_BASE + "/chat", json=body, headers=_hk_headers(),
                          timeout=(15, timeout), stream=True)
    except Exception as e:
        raise EMError(f"hk: {str(e)[:60]}")
    if r.status_code != 200:
        if r.status_code == 429:
            HK_LIMIT["until"] = _t.time() + 600
        elif r.status_code in (400, 500) and model_id in MS.get("hk_ok", {}):
            MS["hk_ok"].pop(model_id, None)
            MS.setdefault("hk_bad", {})[model_id] = {"code": r.status_code, "t": _t.time()}
            _ms_save()
        raise EMError(f"hk: {r.status_code}")
    out = []
    err = None
    paywall = False
    for line in r.text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        tok = line[5:].strip()
        if not tok or tok == "[ERROR]":
            continue
        if tok.startswith("{"):
            try:
                j = json.loads(tok)
            except Exception:
                continue
            msg = str(j.get("message") or "")
            if j.get("error") or "error" in str(j.get("error", "")).lower():
                err = msg[:90]
                if "Payment Required" in msg or "402" in msg or "credits" in msg.lower():
                    paywall = True
                break
            for key in ("content", "text", "answer", "token", "delta"):
                v = j.get(key)
                if isinstance(v, str) and v:
                    out.append(v)
                    break
            continue
        out.append(tok)
    ans = "".join(out).strip()
    if paywall:
        HK_LIMIT["until"] = _hk_quota_ts()
        if MS.get("hk_ok"):
            MS["hk_ok"].clear()
            _ms_save()
            print("[HK] کرێکی سەرەوە بەتاڵ — hk_ok پاککرایەوە تا چاک بوو", flush=True)
        raise EMError("hk: 402 upstream → دیلی تا نیوەشەوی UTC")
    if not ans:
        raise EMError(f"hk: {err or 'وەڵام بەتاڵ'}")
    return ans


def hk_servers():
    labels = dict(HK_CATALOG)
    out = []
    for mid in list(MS.get("hk_ok", {}).keys())[:12]:
        label = labels.get(mid, mid.split("/")[-1])
        slug = re.sub(r'[^a-z0-9.]+', '-', str(mid).lower()).strip('-').replace('/', '-')
        out.append({"id": f"hk-{slug}", "name": f"{label} (Heck)",
                    "model_id": mid, "kind": "hk"})
    return out


def sync_hk_models(force=False):
    """ئۆتۆ-ئەپدێتی heck: پشکنینی زیندوو — ٤٠٢ (کرێکی بەتاڵ) → هیچ؛ سەرکەوتن → هەموو کاتالۆگەکە ✅
       نیو کاتژمێر لە کاتی مردوودا (زیندووبوونەوەی خێرا)، ٦ کاتژمێر لە کاتی زیندوودا"""
    import time as _t
    ok_now = bool(MS.get("hk_ok"))
    ttl = 21600 if ok_now else 1800
    if not force and _t.time() - MS_T.get("hk", 0.0) < ttl:
        return
    MS_T["hk"] = _t.time()
    probe = "deepseek/deepseek-v4-flash"
    try:
        a = hk_chat([{"role": "user", "content": "Reply with exactly: OK"}], probe, timeout=45)
        alive = bool(a)
    except Exception as e:
        alive = False
        msg = str(e)[:70]
        if "402" in msg or "credit" in msg.lower():
            print(f"[HK-SYNC] کرێکی سەرەوە بەتاڵە ({msg}) — چاوەڕوانی پڕکردنەوە", flush=True)
        else:
            print(f"[HK-SYNC] پشکنین شکات: {msg}", flush=True)
    if alive:
        added = 0
        for mid, _lbl in HK_CATALOG:
            if mid not in MS.get("hk_ok", {}):
                MS.setdefault("hk_ok", {})[mid] = {"t": _t.time()}
                added += 1
        for mid in list(MS.get("hk_bad", {}).keys()):
            MS["hk_bad"].pop(mid, None)
        if added or not ok_now:
            _ms_save()
        print(f"[HK-SYNC] heck زیندووە ✅ {added} مۆدێڵ چالاک بوون (hk_ok={len(MS['hk_ok'])})", flush=True)
    elif ok_now and not MS.get("hk_ok"):
        _ms_save()


# ══════════ HuggingFace Inference (router.huggingface.co) — §2.23 — تۆکنی yusfkarim1028 ══════════
HF_TOKEN = "hf_" + "ZNGBNvoPbHFpqMVMscrJpUHhfHJoKnvBeQ"  # yusfkarim1028
HF_BASE = "https://router.huggingface.co/v1"
HF_LIMIT = {"until": 0.0}
_HF_SYNC = {"t": 0.0}


def _hf_headers(ct=True):
    hd = {"Authorization": f"Bearer {HF_TOKEN}", "User-Agent": "Mozilla/5.0"}
    if ct:
        hd["Content-Type"] = "application/json"
    return hd


def hf_chat(messages, model_id="deepseek-ai/DeepSeek-V4.1-Flash", timeout=110):
    """چاتی HF Inference — OpenAI-ستایل؛ 402 = کرێتی مانگانە (دیلی تا یەکی مانگ)؛ 429 = ١٠ خولەک"""
    import time as _t
    if _t.time() < HF_LIMIT["until"]:
        raise EMError("hf: credit cooldown")
    body = {"model": model_id, "messages": messages[-24:], "max_tokens": 1200}
    try:
        r = requests.post(HF_BASE + "/chat/completions", json=body,
                          headers=_hf_headers(), timeout=(15, timeout))
    except Exception as e:
        raise EMError(f"hf: {str(e)[:60]}")
    if r.status_code != 200:
        if r.status_code == 402:
            # کرێتی مانگانە تەواو — دیلی تا یەکی مانگی داهاتوو + پاککردنەوەی مینیو
            now = _t.time()
            nxt = (_t.gmtime(now).tm_year + (1 if _t.gmtime(now).tm_mon == 12 else 0),
                   1 if _t.gmtime(now).tm_mon == 12 else _t.gmtime(now).tm_mon + 1, 1)
            import calendar as _cal
            HF_LIMIT["until"] = _cal.timegm(nxt + (0, 0, 0)) + 300
            if MS.get("hf_ok"):
                MS["hf_ok"].clear()
                _ms_save()
                print("[HF] کرێتی تەواو — hf_ok پاککرایەوە تا ڕێککەوتنی مانگ", flush=True)
            raise EMError("hf: 402 → دیلی تا مانگی داهاتوو")
        if r.status_code == 429:
            HF_LIMIT["until"] = _t.time() + 600
            raise EMError("hf: 429 → دیلی ١٠ خولەک")
        # مردوو لە ترافیکی ڕاستەقینە (400/404/503) → لە hf_ok بۆ hf_bad (دووبارە ٢٤ کاتژمێر)
        if r.status_code in (400, 404, 503) and model_id in MS.get("hf_ok", {}):
            MS["hf_ok"].pop(model_id, None)
            MS.setdefault("hf_bad", {})[model_id] = {"code": r.status_code, "t": _t.time()}
            _ms_save()
            print(f"[HF] مردوو لە چات: {model_id} ({r.status_code}) — لابرا", flush=True)
        raise EMError(f"hf: {r.status_code}")
    try:
        m = r.json()["choices"][0]["message"]
    except Exception:
        raise EMError("hf: parse")
    return (m.get("content") or "").strip()


def hf_servers():
    labels = {}
    out = []
    for mid in list(MS.get("hf_ok", {}).keys())[:40]:
        tail = str(mid).split("/")[-1]
        label = re.sub(r'[-_]', ' ', tail).strip()
        slug = re.sub(r'[^a-z0-9.]+', '-', str(mid).lower()).strip('-').replace('/', '-')
        out.append({"id": f"hf-{slug}", "name": f"{label} (HF)",
                    "model_id": mid, "kind": "hf"})
    return out


def sync_hf_models(force=False):
    """ڕاکێشانی ئۆتۆماتیکی مۆدێڵەکانی HF:
       - کاتالۆگی زیندوو لە /v1/models (لابردنی ئەوانەی HF لابراون — یاسای بەکارهێنەر)
       - پشکنینی نوێیەکان (١٠/خول) → هەر کامێک وەڵام دا بگاتە hf_ok
       - مردووەکان (پشکنین/چات شکات) → hf_bad (دووبارە ٢٤ کاتژمێر)
       خول: ٦ کاتژمێر"""
    import time as _t
    if not force and _t.time() - _HF_SYNC["t"] < 21600:
        return
    _HF_SYNC["t"] = _t.time()
    try:
        r = requests.get(HF_BASE + "/models", headers={"User-Agent": "Mozilla/5.0"}, timeout=(10, 30))
        items = r.json().get("data") or []
    except Exception as e:
        print(f"[HF-SYNC] کاتالۆگ هەڵە: {str(e)[:70]}", flush=True)
        return
    catalog = {m.get("id") for m in items if m.get("id")}
    # ١) لابردنی ئەوانەی لە کاتالۆگ نەماون (مردوو/لابراو لەلایەن HF)
    removed = [mid for mid in list(MS.get("hf_ok", {}).keys()) if mid not in catalog]
    for mid in removed:
        MS["hf_ok"].pop(mid, None)
        print(f"[HF-SYNC] لابرا لە کاتالۆگ: {mid}", flush=True)
    # ٢) زیندووکردنەوەی bad ە کۆن (٢٤ کاتژمێر)
    for mid in list(MS.get("hf_bad", {}).keys()):
        if _t.time() - float(MS["hf_bad"][mid].get("t") or 0) > 86400:
            MS["hf_bad"].pop(mid, None)
    # ٣) پشکنینی نوێیەکان (١٠/خول)
    probed = 0
    added = 0
    for mid in catalog:
        if mid in MS.get("hf_ok", {}) or mid in MS.get("hf_bad", {}) or probed >= 10:
            continue
        probed += 1
        try:
            rr = requests.post(HF_BASE + "/chat/completions",
                               json={"model": mid, "messages": [{"role": "user", "content": "Reply: OK"}], "max_tokens": 8},
                               headers=_hf_headers(), timeout=(10, 40))
            if rr.status_code == 200 and (rr.json().get("choices") or [{}])[0].get("message", {}).get("content"):
                MS.setdefault("hf_ok", {})[mid] = {"t": _t.time()}
                added += 1
                print(f"[HF-SYNC] نوێ ✅ {mid}", flush=True)
            elif rr.status_code == 402:
                import calendar as _cal
                g = _t.gmtime(_t.time())
                nxt = (g.tm_year + (1 if g.tm_mon == 12 else 0), 1 if g.tm_mon == 12 else g.tm_mon + 1, 1)
                HF_LIMIT["until"] = _cal.timegm(nxt + (0, 0, 0)) + 300
                if MS.get("hf_ok"):
                    MS["hf_ok"].clear()
                    print("[HF-SYNC] کرێتی مانگانە تەواو — hf_ok پاککرایەوە", flush=True)
                _ms_save()
                break
            else:
                MS.setdefault("hf_bad", {})[mid] = {"code": rr.status_code, "t": _t.time()}
        except Exception as e:
            MS.setdefault("hf_bad", {})[mid] = {"err": str(e)[:60], "t": _t.time()}
        _t.sleep(0.6)
    if added or removed:
        _ms_save()
    print(f"[HF-SYNC] کاتالۆگ={len(catalog)} | نوێ={added} | لابرا={len(removed)} | hf_ok={len(MS.get('hf_ok', {}))}", flush=True)


# ══════════ Akash Chat (chat.akash.network) — §2.24 — میوان: session_token + AI-SDK v5 ══════════
AKA_BASE = "https://chat.akash.network"
AKA_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
AKA_LIMIT = {"until": 0.0}
_AKA = {"ses": None, "t": 0.0}
_AKA_NEUTRAL = "You are a helpful assistant. Follow the user's instructions precisely."
_AKA_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def _aka_headers():
    return {"User-Agent": AKA_UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9",
            "Origin": AKA_BASE, "Referer": AKA_BASE + "/",
            "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin"}


def _aka_session(force=False):
    """session_token: GET / → GET /api/auth/session → POST refresh (فلۆوی براوزەر)"""
    import time as _t
    if not force and _AKA["ses"] and _t.time() - _AKA["t"] < 43200:
        return _AKA["ses"]
    s = requests.Session()
    s.headers.update(_aka_headers())
    try:
        s.get(AKA_BASE + "/", timeout=(10, 20))
        r = s.get(AKA_BASE + "/api/auth/session", timeout=(10, 20))
        if r.status_code != 200:
            raise EMError(f"aka: session {r.status_code}")
        s.post(AKA_BASE + "/api/auth/session/refresh/", json={}, timeout=(10, 20))
    except EMError:
        raise
    except Exception as e:
        raise EMError(f"aka: {str(e)[:60]}")
    _AKA["ses"] = s
    _AKA["t"] = _t.time()
    return s


def aka_chat(messages, model_id="openai-gpt-oss-120b", timeout=110):
    """چاتی akash — سیستەم-پرۆمپت لە مێژوو دەهێنرێت (بەتاڵ = نیوتراڵ)؛ 403 سێشن → ڕۆتەیشن"""
    import time as _t
    if _t.time() < AKA_LIMIT["until"]:
        raise EMError("aka: cooldown")
    sys_content = ""
    rest = []
    for m in messages:
        if m.get("role") == "system" and not sys_content:
            sys_content = m.get("content") or ""
        elif m.get("content"):
            rest.append(m)
    if not sys_content:
        sys_content = _AKA_NEUTRAL
    last_err = None
    for attempt in range(2):
        try:
            s = _AKA["ses"] if (_AKA["ses"] and attempt == 0) else _aka_session(force=(attempt == 1))
        except Exception as e:
            last_err = e
            continue
        cid = "".join(random.choices(_AKA_CHARS, k=12))
        hist = rest[-10:]
        body = {"id": cid,
                "messages": [{"role": m.get("role", "user"), "content": m.get("content") or "",
                              "parts": [{"type": "text", "text": m.get("content") or ""}]} for m in hist],
                "model": model_id, "system": sys_content, "temperature": 0.6, "topP": 0.95, "context": []}
        try:
            r = s.post(AKA_BASE + "/api/chat/", json=body, timeout=(15, timeout), stream=True)
        except Exception as e:
            last_err = EMError(f"aka: {str(e)[:60]}")
            continue
        if r.status_code == 403 or r.status_code == 401:
            _AKA["ses"] = None
            last_err = EMError(f"aka: {r.status_code} سێشن")
            continue
        if r.status_code == 429:
            AKA_LIMIT["until"] = _t.time() + 900
            raise EMError("aka: 429 → دیلی ١٥ خولەک")
        if r.status_code != 200:
            if r.status_code in (400, 500) and model_id in MS.get("aka_ok", {}):
                MS["aka_ok"].pop(model_id, None)
                MS.setdefault("aka_bad", {})[model_id] = {"code": r.status_code, "t": _t.time()}
                _ms_save()
            raise EMError(f"aka: {r.status_code}")
        raw = b""
        try:
            for ch in r.iter_content(512):
                raw += ch
                if len(raw) > 120_000:
                    break
        except Exception:
            pass
        t = raw.decode("utf-8", "replace")
        texts = re.findall(r'^0:"(.*)"', t, re.M)
        try:
            ans = "".join(json.loads(f'"{x}"') for x in texts)
        except Exception:
            ans = "".join(texts)
        ans = ans.strip()
        if ans:
            return ans
        last_err = EMError("aka: وەڵام بەتاڵ")
    raise last_err or EMError("aka: شکست")


def aka_servers():
    out = []
    for mid in list(MS.get("aka_ok", {}).keys())[:6]:
        label = "GPT-OSS 120B" if "gpt-oss" in str(mid) else str(mid).replace("-", " ").title()
        slug = re.sub(r'[^a-z0-9.]+', '-', str(mid).lower()).strip('-')
        out.append({"id": f"aka-{slug}", "name": f"{label} (Akash)",
                    "model_id": mid, "kind": "aka"})
    return out


def sync_akash_models(force=False):
    """ئۆتۆ-ئەپدێتی akash: /api/models گشتی — تەنها دەقی (AkashGen/وێنە دەرباز)؛
       لابراوەکان لە کاتالۆگ خۆکارانە لابرددرێن (یاسای بەکارهێنەر)"""
    import time as _t
    if not force and _t.time() - MS_T.get("aka", 0.0) < 21600:
        return
    MS_T["aka"] = _t.time()
    try:
        r = requests.get(AKA_BASE + "/api/models", headers=_aka_headers(), timeout=(10, 20))
        items = r.json() or []
    except Exception as e:
        print(f"[AKA-SYNC] هەڵە: {str(e)[:70]}", flush=True)
        return
    text_models = {m.get("id") for m in items
                   if m.get("id") and m.get("api_id") and "gen" not in str(m.get("id", "")).lower()
                   and "image" not in str(m.get("description", "")).lower()}
    removed = [mid for mid in list(MS.get("aka_ok", {}).keys()) if mid not in text_models]
    for mid in removed:
        MS["aka_ok"].pop(mid, None)
        print(f"[AKA-SYNC] لابرا: {mid}", flush=True)
    added = 0
    for mid in text_models:
        if mid not in MS.get("aka_ok", {}) and mid not in MS.get("aka_bad", {}):
            try:
                code, ans = (None, None)
                s = _aka_session()
                cid = "".join(random.choices(_AKA_CHARS, k=12))
                body = {"id": cid, "messages": [{"role": "user", "content": "Reply: OK", "parts": [{"type": "text", "text": "Reply: OK"}]}],
                        "model": mid, "system": _AKA_NEUTRAL, "temperature": 0.6, "topP": 0.95, "context": []}
                rr = s.post(AKA_BASE + "/api/chat/", json=body, timeout=(10, 40), stream=True)
                if rr.status_code == 200:
                    MS.setdefault("aka_ok", {})[mid] = {"t": time.time()}
                    added += 1
                    print(f"[AKA-SYNC] نوێ ✅ {mid}", flush=True)
                elif rr.status_code == 429:
                    AKA_LIMIT["until"] = time.time() + 900
                    break
                else:
                    MS.setdefault("aka_bad", {})[mid] = {"code": rr.status_code, "t": time.time()}
            except Exception as e:
                MS.setdefault("aka_bad", {})[mid] = {"err": str(e)[:50], "t": time.time()}
    if added or removed:
        _ms_save()
    print(f"[AKA-SYNC] کاتالۆگ={len(text_models)} | نوێ={added} | لابرا={len(removed)} | aka_ok={len(MS.get('aka_ok', {}))}", flush=True)


# ══════════ Hotbot (www.hotbot.com) — §2.25 — ٤ چات/٥خولەک بە IP (کۆنترۆڵکراو) ══════════
HB_BASE = "https://www.hotbot.com"
HB_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
HB_LIMIT = {"until": 0.0}
_HB_SYNC = {"t": 0.0}


def hb_chat(messages, model_id="hotbot-chat", timeout=110):
    """چاتی hotbot — یەک مۆدێڵ؛ ٤ چات بە IP، پاش بەتاڵی 200 → دیلی ٥ خولەک"""
    import time as _t
    if _t.time() < HB_LIMIT["until"]:
        raise EMError("hb: cooldown")
    last = ""
    for m in reversed(messages):
        if m.get("role") == "user" and m.get("content"):
            last = m["content"]
            break
    if not last:
        raise EMError("hb: هیچ پرسیار")
    import uuid as _uuid
    cid = str(_uuid.uuid4())
    try:
        requests.get(HB_BASE + "/", headers={"User-Agent": HB_UA}, timeout=(10, 20))
    except Exception:
        pass
    try:
        rm = requests.post(HB_BASE + "/api/moderate",
                           json={"text": last[-800:], "imageUrls": [], "chatId": cid, "requestType": "text"},
                           headers={"User-Agent": HB_UA, "Content-Type": "application/json",
                                    "Origin": HB_BASE, "Referer": HB_BASE + "/"}, timeout=(10, 20))
        if rm.status_code == 200 and (rm.json() or {}).get("flagged"):
            raise EMError("hb: moderate بلۆک")
    except EMError:
        raise
    except Exception:
        pass
    hist = [{"role": m.get("role", "user"), "content": m.get("content") or ""}
            for m in messages if m.get("content")][-12:]
    try:
        r = requests.post(HB_BASE + "/api/chat",
                          json={"messages": hist, "model": "hotbot-chat", "chatId": cid,
                                "effort": "light", "camp": False},
                          headers={"User-Agent": HB_UA, "Content-Type": "application/json",
                                   "Origin": HB_BASE, "Referer": HB_BASE + "/"},
                          timeout=(15, timeout), stream=True)
    except Exception as e:
        raise EMError(f"hb: {str(e)[:60]}")
    if r.status_code != 200:
        if r.status_code == 429:
            HB_LIMIT["until"] = _t.time() + 300
        raise EMError(f"hb: {r.status_code}")
    try:
        raw = r.content
    except Exception:
        raw = b""
    t = raw.decode("utf-8", "replace")
    ans_parts = []
    for m2 in re.finditer(r'data: (\{"content":".*?"\})', t):
        try:
            ans_parts.append(json.loads(m2.group(1)).get("content", ""))
        except Exception:
            pass
    ans = "".join(ans_parts).strip()
    if not ans:
        HB_LIMIT["until"] = _t.time() + 300
        raise EMError("hb: بەتاڵ → دیلی ٥ خولەک (کوانتا)")
    return ans


def hb_servers():
    out = []
    if "hotbot-chat" in MS.get("hb_ok", {}) or not MS.get("hb_ok"):
        out.append({"id": "hb-hotbot-chat", "name": "HotBot Chat", "model_id": "hotbot-chat", "kind": "hb"})
    return out


def sync_hb_models(force=False):
    """ئۆتۆ-ئەپدێتی hotbot: پشکنینی زیندوو (٦ کاتژمێر) — مۆدێڵی تاک"""
    import time as _t
    if not force and _t.time() - _HB_SYNC["t"] < 21600:
        return
    _HB_SYNC["t"] = _t.time()
    try:
        a = hb_chat([{"role": "user", "content": "Reply with: OK"}], timeout=45)
        if a:
            if "hotbot-chat" not in MS.get("hb_ok", {}):
                MS.setdefault("hb_ok", {})["hotbot-chat"] = {"t": _t.time()}
                _ms_save()
            print("[HB-SYNC] hotbot زیندووە ✅", flush=True)
    except Exception as e:
        print(f"[HB-SYNC] {str(e)[:70]}", flush=True)


# ══════════ GadegetKit (gadegetkit.com) — §2.26 — glm-4-flash، signature-flow، بێ لیمیت دیارکراو ══════════
GK_BASE = "https://www.gadegetkit.com"
GK_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
GK_LIMIT = {"until": 0.0}
_GK_SYNC = {"t": 0.0}


def gk_chat(messages, model_id="glm-4-flash", timeout=150):
    """چاتی gadegetkit — generate-signature ← ai-text/chat (سیستەم-پرۆمپت لە messages)"""
    import time as _t
    if _t.time() < GK_LIMIT["until"]:
        raise EMError("gk: cooldown")
    hist = [{"role": m.get("role", "user"), "content": m.get("content") or ""}
            for m in messages if m.get("content")][-16:]
    if not hist:
        raise EMError("gk: هیچ نامە")
    try:
        s = requests.Session()
        s.headers.update({"User-Agent": GK_UA, "Content-Type": "application/json",
                          "Origin": GK_BASE, "Referer": GK_BASE + "/ai-tools/chatbot"})
        s.get(GK_BASE + "/ai-tools/chatbot", timeout=(10, 25))
        ts = str(int(_t.time() * 1000))
        rs = s.post(GK_BASE + "/api/internal/generate-signature",
                    json={"timestamp": int(ts), "path": "/api/ai-text/chat"}, timeout=(10, 25))
        sig = (rs.json() or {}).get("signature")
        if not sig:
            raise EMError("gk: signature نییە")
        r = s.post(GK_BASE + "/api/ai-text/chat", json={"messages": hist, "locale": "en"},
                   headers={"x-timestamp": ts, "x-signature": sig}, timeout=(15, timeout))
    except EMError:
        raise
    except Exception as e:
        raise EMError(f"gk: {str(e)[:60]}")
    if r.status_code != 200:
        if r.status_code == 429:
            GK_LIMIT["until"] = _t.time() + 600
        raise EMError(f"gk: {r.status_code}")
    try:
        j = r.json()
    except Exception:
        raise EMError("gk: parse")
    ans = (j.get("text") or "").strip()
    if not ans or not j.get("success"):
        raise EMError("gk: وەڵام بەتاڵ")
    return ans


def gk_servers():
    out = []
    if "glm-4-flash" in MS.get("gk_ok", {}) or not MS.get("gk_ok"):
        out.append({"id": "gk-glm-4-flash", "name": "GLM 4 Flash (GK)", "model_id": "glm-4-flash", "kind": "gk"})
    return out


def sync_gk_models(force=False):
    """ئۆتۆ-ئەپدێتی gadegetkit: پشکنینی زیندوو (٦ کاتژمێر)"""
    import time as _t
    if not force and _t.time() - _GK_SYNC["t"] < 21600:
        return
    _GK_SYNC["t"] = _t.time()
    try:
        a = gk_chat([{"role": "user", "content": "Reply with: OK"}], timeout=60)
        if a:
            if "glm-4-flash" not in MS.get("gk_ok", {}):
                MS.setdefault("gk_ok", {})["glm-4-flash"] = {"t": _t.time()}
                _ms_save()
            print("[GK-SYNC] gadegetkit زیندووە ✅", flush=True)
    except Exception as e:
        print(f"[GK-SYNC] {str(e)[:70]}", flush=True)


# ══════════ GizAI (giz.ai) — §2.27 — کوانتا بۆ هەر مۆدێڵ ~١ کاتژمێر (بەکارهێنەر: لیمیت مەیەڵە) ══════════
GZ_BASE = "https://www.giz.ai"
GZ_CDN = "https://cdnwww.giz.ai/api/model/choices/textGeneration"
GZ_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
# ناسنامەی نەناسراو (کوکی pfb9) — سەرڤەر بەند بە IP نییە
GZ_PFB9 = "c7380813ca955a386914044983fbcf6a082dbf2bea2eb91917b37ba33d6ff05b"
GZ_SKIP = {"dynamic"}  # dynamic لە ڕێپلەی 400 دەدات (resolve ی session ی وێب دەوێت)
GZ_COOLDOWN = {"quota": 3700.0, "login": 3700.0}  # 401 = دوای کوانتاش دێتەوە → کاتژمێر
_GZ_BADC = {}  # model → cooldown تا
_GZ_SYNC = {"t": 0.0, "thread": None, "labels": {}}


def _gz_rid(n):
    import secrets as _sc, string as _st
    return "".join(_sc.choice(_st.ascii_letters + _st.digits + "-_") for _ in range(n))


def gz_chat(messages, model_id, timeout=110):
    """چاتی GizAI — session ی نەناسراو ← infer → {"status":"completed","output":…}"""
    import time as _t
    if _t.time() < _GZ_BADC.get(model_id, 0):
        raise EMError("gz: cooldown")
    hist = [{"type": (m.get("role") or "user"), "content": m.get("content") or ""}
            for m in messages if m.get("content")][-12:]
    if not hist:
        raise EMError("gz: هیچ نامە")
    try:
        s = requests.Session()
        s.headers.update({"User-Agent": GZ_UA, "Content-Type": "application/json",
                          "Origin": GZ_BASE, "Referer": GZ_BASE + "/assistant?mode=chat&baseModel=dynamic"})
        s.cookies.set("pfb9", GZ_PFB9, domain="www.giz.ai")
        r0 = s.post(GZ_BASE + "/api/data/spaces/spaceServer.createAnonymousSession",
                    json={"visitorId": _gz_rid(32), "session": {"mode": "chat", "shared": False,
                          "modeInput": {"baseModel": "dynamic", "settings": {"character": "AI", "responseMode": "text"},
                          "reasoning": {"level": "low", "mode": "default"}, "context": "general",
                          "reference": "auto", "showChoices": False}}}, timeout=(10, 25))
        sid = (r0.json() or {}).get("sessionId") if r0.status_code in (200, 201) else None
        if not sid:
            raise EMError(f"gz: session {r0.status_code}")
        inst = _gz_rid(21)
        inf = {"model": model_id,
               "input": {"messages": hist, "sessionId": sid, "mode": "chat",
                         "settings": {"character": "AI", "responseMode": "text"}, "context": "general"},
               "subscribeId": _gz_rid(22), "instanceId": inst}
        r = s.post(GZ_BASE + "/api/data/users/inferenceServer.infer", json=inf,
                   headers={"x-giz-instance-id": inst}, timeout=(15, timeout))
    except EMError:
        raise
    except Exception as e:
        raise EMError(f"gz: {str(e)[:60]}")
    if r.status_code == 429:
        _GZ_BADC[model_id] = _t.time() + GZ_COOLDOWN["quota"]
        raise EMError("gz: کوانتای مۆدێڵ (~١ کاتژمێر)")
    if r.status_code == 401:
        _GZ_BADC[model_id] = _t.time() + GZ_COOLDOWN["login"]
        raise EMError("gz: لۆگین-واڵ")
    if r.status_code != 201 and r.status_code != 200:
        raise EMError(f"gz: {r.status_code}")
    try:
        j = r.json()
    except Exception:
        raise EMError("gz: parse")
    if (j.get("status") or "completed") != "completed":
        raise EMError(f"gz: status={j.get('status')}")
    ans = (j.get("output") or "").strip()
    if not ans:
        raise EMError("gz: وەڵام بەتاڵ")
    return ans


def _gz_slug(v):
    import re as _re
    sl = _re.sub(r"[^a-zA-Z0-9]+", "-", v).strip("-").lower()
    return sl[:60] or "model"


def gz_servers():
    out = []
    for v, lbl in sorted(_GZ_SYNC.get("catalog", {}).items()):
        out.append({"id": f"gz-{_gz_slug(v)}", "name": f"{lbl} (Giz)", "model_id": v, "kind": "gz"})
    return out


def _gz_parse_catalog(raw):
    """JS-catalog → لیستی {value, label, free0} — سکەنی ئۆبجێکت-بە-ئۆبجێکت (خێرا، بێ json5)"""
    import re as _re
    i = raw.find("items:[")
    if i < 0:
        return []
    t = raw[i + len("items:"):]
    out = []
    seen = set()
    pos = 0
    n = len(t)
    while True:
        st = t.find("{value:", pos)
        if st < 0 or st >= n:
            break
        depth = 0
        instr = None
        esc = False
        en = -1
        lim = min(st + 9000, n)
        for idx in range(st, lim):
            ch = t[idx]
            if instr:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == instr:
                    instr = None
                continue
            if ch in ("`", '"', "'"):
                instr = ch
                esc = False
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    en = idx
                    break
        if en < 0:
            pos = st + 7
            continue
        obj = t[st:en + 1]
        pos = en + 1
        mv = _re.search(r'value:\s*["\'`]([^"\'`]{1,80})["\'`]', obj)
        if not mv:
            continue
        v = mv.group(1)
        if v in seen:
            continue
        seen.add(v)
        ml = _re.search(r'label:\s*["\'`]([^"\'`]{0,120})["\'`]', obj)
        free0 = bool(_re.search(r'free:\s*\{[^}]*throttleLimit:\s*0', obj))
        out.append({"value": v, "label": (ml.group(1) if ml else v), "free0": free0})
    return out


def sync_giz_models(force=False):
    """ئۆتۆ-ئەپدێتی GizAI: کاتالۆگی CDN (٦ کاتژمێر) — بێ probe (کوانتا نەسوتێت)؛
    فیلتەر: gateway/* (پارەدار) و free-limit-0 و شاراوە دەر دەکرێن"""
    import time as _t
    if not force and _t.time() - _GZ_SYNC["t"] < 21600:
        return
    try:
        r = requests.get(GZ_CDN, headers={"User-Agent": GZ_UA}, timeout=(10, 40))
        if r.status_code != 200:
            print(f"[GZ-SYNC] catalog {r.status_code}", flush=True)
            return
        cands = _gz_parse_catalog(r.text)
        cat = {}
        for c in cands:
            v = c["value"]
            if v in GZ_SKIP or v.startswith("gateway/") or c.get("free0"):
                continue
            cat[v] = c["label"]
        _GZ_SYNC["catalog"] = cat
        _GZ_SYNC["t"] = _t.time()
        print(f"[GZ-SYNC] کاتالۆگ {len(cands)} → تۆمارکراو {len(cat)}", flush=True)
    except Exception as e:
        print(f"[GZ-SYNC] {str(e)[:80]}", flush=True)


# ══════════ Pi (pi.ai) — §2.28 — curl_cffi (CF-impersonate) + SSE partial ══════════
PI_BASE = "https://pi.ai"
PI_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
PI_STATE = {"s": None, "did": None}
PI_LIMIT = {"until": 0.0}
_PI_SYNC = {"t": 0.0}


def _pi_headers():
    return {"Origin": PI_BASE, "Referer": PI_BASE + "/talk", "x-api-version": "5",
            "x-client-timezone": "UTC", "User-Agent": PI_UA}


def _pi_session():
    """نشستی curl_cffi — بەکارهێنەری نەناسراو (chat/start + legal-accept)"""
    from curl_cffi import requests as _cr
    import uuid as _u
    s = _cr.Session(impersonate="chrome")
    did = str(_u.uuid4())
    r = s.post(PI_BASE + "/api/chat/start",
               json={"distinctId": did, "deviceFingerprint": "pnjfnj"},
               headers=_pi_headers(), timeout=(15, 30))
    if r.status_code != 200:
        raise EMError(f"pi: start {r.status_code}")
    r2 = s.post(PI_BASE + "/api/user/legal-accept",
                json={"name": "Yusf", "ageVerified": True,
                      "useDataToImproveModelsConsent": True,
                      "useEmotionRecognitionOnVoiceConsent": True},
                headers=_pi_headers(), timeout=(15, 30))
    PI_STATE["s"] = s
    PI_STATE["did"] = did
    return s, did


def pi_chat(messages, model_id="pi-chat", timeout=110):
    """چاتی Pi — مێژوو فلێت دەکرێت بۆ یەک دەق؛ SSE partial → یەک وەڵام"""
    import time as _t, uuid as _u, json as _j
    if _t.time() < PI_LIMIT["until"]:
        raise EMError("pi: cooldown")
    lines = []
    for m in messages[-12:]:
        role = m.get("role")
        c = (m.get("content") or "").strip()
        if not c:
            continue
        if role == "system":
            lines.append("[Instructions] " + c)
        elif role == "user":
            lines.append("[User] " + c)
        else:
            lines.append("[Assistant] " + c)
    if not lines:
        raise EMError("pi: هیچ نامە")
    lines.append("[Assistant]")
    text = "\n".join(lines)[-6000:]
    import re as _re
    text = _re.sub(r"\[User\]\s*\[Assistant\]", "", text)
    last = ""
    for attempt in (1, 2):
        try:
            s = PI_STATE.get("s")
            did = PI_STATE.get("did")
            if s is None:
                s, did = _pi_session()
            r = s.post(PI_BASE + "/api/v2/chat",
                       json={"text": text, "conversation": "",
                             "eqDistinctId": did, "eqSessionId": str(_u.uuid4()),
                             "clientId": str(_u.uuid4())},
                       headers=_pi_headers(), timeout=(15, timeout), stream=True)
            if r.status_code in (401, 403, 429) and attempt == 1:
                PI_STATE["s"] = None
                if r.status_code == 429:
                    PI_LIMIT["until"] = _t.time() + 300
                continue
            if r.status_code != 200:
                raise EMError(f"pi: {r.status_code}")
            parts = []
            buf = ""
            for ch in r.iter_content(chunk_size=None):
                buf += ch.decode("utf-8", "replace")
                while "\n" in buf:
                    ln, buf = buf.split("\n", 1)
                    ln = ln.strip()
                    if ln.startswith("data:"):
                        try:
                            d = _j.loads(ln[5:].strip())
                            t2 = d.get("text")
                            if isinstance(t2, str):
                                parts.append(t2)
                        except Exception:
                            pass
            last = "".join(parts).strip()
            if last:
                return last
            # بەتاڵ — ئەگەر trial تەواو بووە، نشستی نوێ
            PI_STATE["s"] = None
            continue
        except EMError:
            raise
        except Exception as e:
            PI_STATE["s"] = None
            if attempt == 2:
                raise EMError(f"pi: {str(e)[:60]}")
    if last:
        return last
    raise EMError("pi: وەڵام بەتاڵ")


def pi_servers():
    out = []
    if "pi-chat" in MS.get("pi_ok", {}) or not MS.get("pi_ok"):
        out.append({"id": "pi-pi-chat", "name": "Pi (pi.ai)", "model_id": "pi-chat", "kind": "pi"})
    return out


def sync_pi_models(force=False):
    """ئۆتۆ-ئەپدێتی Pi: چاتی تاقیکردنەوە (٦ کاتژمێر) — بەکارهێنەری نوێ = کوانتای نوێ"""
    import time as _t
    if not force and _t.time() - _PI_SYNC["t"] < 21600:
        return
    _PI_SYNC["t"] = _t.time()
    try:
        PI_STATE["s"] = None  # نشستی نوێ = بەکارهێنەری نوێ
        a = pi_chat([{"role": "user", "content": "Reply with: OK"}], timeout=60)
        if a:
            if "pi-chat" not in MS.get("pi_ok", {}):
                MS.setdefault("pi_ok", {})["pi-chat"] = {"t": _t.time()}
                _ms_save()
            print("[PI-SYNC] pi زیندووە ✅", flush=True)
    except Exception as e:
        print(f"[PI-SYNC] {str(e)[:70]}", flush=True)


# ══════════ ChatbotApp (chat.chatbotapp.ai) — §2.29 — Firebase + حەوزی ئەکاونت + خۆکار-ساینئەپ ══════════
CB_KEY = "AIzaSyBQLxwsoGGyo0DOI-P8IdRWDAE401me8E8"
CB_BASE = "https://api.chatbotapp.ai"
CB_CMS = "https://webcms.chatbotapp.ai/api/ai-models?populate[]=tags&populate[]=examples&populate[]=suggestions&pagination[pageSize]=100"
CB_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
CB_ACC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cb_accounts.json")
CB_FREE_BOTS = {104: "4o-mini", 107: "gpt-4.1-mini", 113: "gpt-5.1", 117: "gpt-5.4-mini",
                200: "gemini-2.5-flash", 202: "gemini-3-flash", 204: "gemini-3.1-flash-lite",
                301: "deepSeek", 302: "deepseek-v4-flash", 502: "claude-4.5-haiku"}
CB_HTTP400_BOTS = {115, 501, 123, 14}  # پێویستیان بە پارامەتری جیاواز
CB_ST = {"tok": None, "uid": None, "tok_t": 0.0, "idx": 0, "next_num": 82412,
         "exhausted": {}, "ensured": {}, "signups": {"date": "", "n": 0}}
_CB_SYNC = {"t": 0.0}
# ئامرازەکان کە چاتی دەقی نین — دەرکراو
CB_SKIP_KEYS = {"link-and-ask", "music-generation", "document", "editor", "ai-search", "superbot", "aiapp", "chatbotapp", "youtube-summarizer", "image-generator", "logo-generator", "tattoo-generator"}


def _cb_load_acc():
    import json as _j
    try:
        d = _j.load(open(CB_ACC_FILE, encoding="utf-8"))
        CB_ST["accounts"] = d.get("accounts") or []
        CB_ST["idx"] = int(d.get("idx") or 0)
        CB_ST["next_num"] = int(d.get("next_num") or 82400)
        CB_ST["exhausted"] = d.get("exhausted") or {}
        CB_ST["signups"] = d.get("signups") or {"date": "", "n": 0}
    except Exception:
        CB_ST["accounts"] = []


def _cb_save_acc():
    import json as _j
    try:
        _j.dump({"accounts": CB_ST.get("accounts") or [], "idx": CB_ST["idx"],
                 "next_num": CB_ST["next_num"], "exhausted": CB_ST.get("exhausted") or {},
                 "signups": CB_ST.get("signups") or {"date": "", "n": 0}},
                open(CB_ACC_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


_cb_load_acc()


def _cb_firebase(ep, email, pw):
    import time as _t
    r = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:{ep}?key={CB_KEY}",
                      json={"email": email, "password": pw, "returnSecureToken": True},
                      headers={"User-Agent": CB_UA}, timeout=(10, 25))
    if r.status_code != 200:
        return None
    j = r.json()
    tok = j.get("idToken")
    if not tok:
        return None
    import base64 as _b
    p = tok.split(".")[1]
    p += "=" * (-len(p) % 4)
    try:
        uid = _b.urlsafe_b64decode(p).decode("utf-8", "replace")
        uid = json.loads(uid).get("user_id") or ""
    except Exception:
        uid = ""
    return tok, uid


def _cb_cur_acc():
    accs = CB_ST.get("accounts") or []
    if not accs:
        return None
    return accs[CB_ST["idx"] % len(accs)]


def _cb_signup_new():
    """ئەکاونتی نوێ — سەرنج: ڕۆژانە زۆر نەبێت"""
    import time as _t, datetime as _dt
    today = _dt.datetime.utcnow().strftime("%Y-%m-%d")
    sg = CB_ST.get("signups") or {"date": "", "n": 0}
    if sg.get("date") != today:
        sg = {"date": today, "n": 0}
    if sg.get("n", 0) >= 20:
        return None
    if len(CB_ST.get("accounts") or []) >= 40:
        return None
    n = CB_ST["next_num"]
    for _ in range(6):
        email = f"komex{n}@duidir.com"
        res = _cb_firebase("signUp", email, email)
        if res:
            CB_ST["accounts"] = (CB_ST.get("accounts") or []) + [{"email": email, "password": email}]
            CB_ST["idx"] = len(CB_ST["accounts"]) - 1
            CB_ST["next_num"] = n + 1
            sg["n"] = sg.get("n", 0) + 1
            CB_ST["signups"] = sg
            _cb_save_acc()
            CB_ST["tok"] = None
            print(f"[CB] ئەکاونتی نوێ ✅ {email}", flush=True)
            return res
        n += 1
    CB_ST["next_num"] = n
    _cb_save_acc()
    return None


def _cb_token():
    import time as _t
    if CB_ST.get("tok") and _t.time() - CB_ST.get("tok_t", 0) < 2700 and CB_ST.get("uid"):
        return CB_ST["tok"], CB_ST["uid"]
    acc = _cb_cur_acc()
    if not acc:
        res = _cb_signup_new()
        if not res:
            raise EMError("cb: هیچ ئەکاونت")
        CB_ST["tok"], CB_ST["uid"] = res
        CB_ST["tok_t"] = _t.time()
        return CB_ST["tok"], CB_ST["uid"]
    res = _cb_firebase("signInWithPassword", acc["email"], acc["password"])
    if not res:
        # ئەکاونتەکە نییە — دواتری
        raise EMError("cb: sign-in شکات")
    CB_ST["tok"], CB_ST["uid"] = res
    CB_ST["tok_t"] = _t.time()
    return CB_ST["tok"], CB_ST["uid"]


def _cb_rotate():
    """ئەکاونتی دواتر — ئەگەر هەمووی تەواو بوو → ئەکاونتی نوێ"""
    accs = CB_ST.get("accounts") or []
    if not accs:
        res = _cb_signup_new()
        return bool(res)
    start = CB_ST["idx"]
    for _ in range(len(accs)):
        CB_ST["idx"] = (CB_ST["idx"] + 1) % len(accs)
        acc = accs[CB_ST["idx"]]
        if str(CB_ST.get("exhausted", {}).get(acc["email"], 0))[:10] == __import__("datetime").datetime.utcnow().strftime("%Y-%m-%d"):
            continue
        CB_ST["tok"] = None
        _cb_save_acc()
        return True
    # هەموو ئەم ڕۆژە تەواون → ئەکاونتی نوێ
    res = _cb_signup_new()
    if res:
        return True
    _cb_save_acc()
    return False


def _cb_slug(v):
    import re as _re
    sl = _re.sub(r"[^a-zA-Z0-9]+", "-", v).strip("-").lower()
    return sl[:60] or "model"


def cb_chat(messages, model_id, timeout=110):
    """چاتی ChatbotApp — مێژوو فلێت + حەوزی ئەکاونت + SSE parts"""
    import time as _t, uuid as _u
    meta = (MS.get("cb_ok") or {}).get(model_id)
    if not meta:
        raise EMError("cb: مۆدێڵ نییە")
    bot_id = meta.get("botId") or 120
    tier = meta.get("tier") or "f"
    if tier == "x":
        max_att = 1
    else:
        max_att = min(len(CB_ST.get("accounts") or [1]) + 1, 8)
    lines = []
    for m in messages[-12:]:
        role = m.get("role")
        c = (m.get("content") or "").strip()
        if not c:
            continue
        if role == "system":
            lines.append("[Instructions] " + c)
        elif role == "user":
            lines.append("[User] " + c)
        else:
            lines.append("[Assistant] " + c)
    if not lines:
        raise EMError("cb: هیچ نامە")
    lines.append("[Assistant]")
    prompt = "\n".join(lines)[-6000:]
    last_err = ""
    for attempt in range(max_att):
        try:
            tok, uid = _cb_token()
        except EMError:
            if not _cb_rotate():
                raise
            continue
        H = {"User-Agent": CB_UA, "Content-Type": "application/json", "accept": "text/event-stream",
             "x_token": tok, "x_user_id": uid, "x_platform": "web", "x_model": str(bot_id),
             "Origin": "https://chat.chatbotapp.ai", "Referer": "https://chat.chatbotapp.ai/"}
        body = {"botId": bot_id, "sessionId": _u.uuid4().hex[:20],
                "userPseudoId": f"{_u.uuid4().int % 10 ** 9}.{int(_t.time())}",
                "hubxId": str(_u.uuid4()),
                "message": {"prompt": prompt, "messageId": str(_u.uuid4())},
                "actions": {"webSearch": False, "createImage": False, "deepSearch": False, "privateSearch": False}}
        try:
            r = requests.post(CB_BASE + "/api/v2/chat", json=body, headers=H,
                              timeout=(15, timeout), stream=True)
        except Exception as e:
            raise EMError(f"cb: {str(e)[:60]}")
        if r.status_code != 200:
            raw = b""
            try:
                for ch in r.iter_content(chunk_size=None):
                    raw += ch
                    if len(raw) > 300:
                        break
            except Exception:
                pass
            msg = ""
            try:
                msg = (json.loads(raw.decode("utf-8", "replace")).get("data") or {}).get("message", "")
            except Exception:
                msg = raw[:60].decode("utf-8", "replace")
            last_err = msg or str(r.status_code)
            if "Insufficient chat credit" in msg:
                if tier == "x":
                    raise EMError("cb: پرێمیۆمی-قورس — بە پارە بەردەستە")
                import datetime as _dt
                acc = _cb_cur_acc()
                if acc:
                    CB_ST.setdefault("exhausted", {})[acc["email"]] = _t.time()
                if not _cb_rotate():
                    raise EMError("cb: کرێدیت هەموو ئەکاونتەکان")
                continue
            if "No agent mapping" in msg:
                MS.setdefault("cb_bad", {})[model_id] = {"t": _t.time(), "why": "no-mapping"}
                MS.get("cb_ok", {}).pop(model_id, None)
                _ms_save()
                raise EMError("cb: مۆدێڵ نەماوە")
            raise EMError(f"cb: {last_err[:60]}")
        parts = []
        agent = ""
        for line in r.iter_lines(decode_unicode=True):
            if not line.startswith("data:"):
                continue
            try:
                d = json.loads(line[5:].strip())
            except Exception:
                continue
            dd = d.get("data") or {}
            if isinstance(dd, dict):
                if dd.get("agent_id"):
                    agent = dd["agent_id"]
                c = dd.get("content")
                if isinstance(c, dict) and c.get("parts"):
                    for p in c["parts"]:
                        if isinstance(p, dict) and p.get("thought"):
                            continue  # پارچەی بیرکردنەوە
                        parts.append((p or {}).get("text", "") if isinstance(p, dict) else str(p))
        # پترن: دێڵتا زیادەکان + ڕووداوی کۆتایی-کۆکراو (وەک Nova §2.32)
        if len(parts) > 1 and parts[-1].startswith("".join(parts[:-1])):
            ans = parts[-1].strip()
        else:
            ans = "".join(parts).strip()
        if ans:
            return ans
        last_err = "بەتاڵ"
        CB_ST["tok"] = None
    raise EMError(f"cb: {last_err[:60] or 'شکست'}")


def cb_servers():
    out = []
    for k, meta in sorted((MS.get("cb_ok") or {}).items()):
        out.append({"id": f"cb-{_cb_slug(k)}", "name": f"{(meta or {}).get('label') or k} (CB)",
                    "model_id": k, "kind": "cb"})
    return out


def sync_cb_models(force=False):
    """ئۆتۆ-ئەپدێتی ChatbotApp: کاتالۆگی webcms (٦ کاتژمێر) — تەنها دەقی بە botId"""
    import time as _t
    if not force and _t.time() - _CB_SYNC["t"] < 21600:
        return
    _CB_SYNC["t"] = _t.time()
    try:
        r = requests.get(CB_CMS, headers={"User-Agent": CB_UA, "Origin": "https://chat.chatbotapp.ai",
                                          "Referer": "https://chat.chatbotapp.ai/"}, timeout=(10, 40))
        if r.status_code != 200:
            print(f"[CB-SYNC] catalog {r.status_code}", flush=True)
            return
        items = (r.json() or {}).get("data") or []
        ok = {}
        for m in items:
            k = (m or {}).get("modelKey") or ""
            if not k or k in CB_SKIP_KEYS:
                continue
            if (m.get("type") or "") != "text":
                continue
            b = m.get("botId")
            if not isinstance(b, int) or b <= 0 or b in CB_HTTP400_BOTS:
                continue
            tier = "f" if b in CB_FREE_BOTS else "x"
            lbl = m.get("title") or k
            if lbl.startswith("models."):
                lbl = k
            ok[k] = {"botId": b, "label": lbl, "tier": tier}
        MS["cb_ok"] = ok
        _ms_save()
        print(f"[CB-SYNC] کاتالۆگ {len(items)} → تۆمارکراو {len(ok)}", flush=True)
    except Exception as e:
        print(f"[CB-SYNC] {str(e)[:80]}", flush=True)


# ══════════ ChatbotAI (chatbotai.co) — §2.30 — Firebase + حەوزی ئەکاونت + خۆکار-ساینئەپ ══════════
CA_KEY = "AIzaSyDHatafp1HL1DKD0Id1UVHPGQY8m_eseAk"
CA_BASE = "https://chatbotai.co"
CA_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
CA_ACC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ca_accounts.json")
CA_ST = {"tok": None, "tok_t": 0.0, "idx": 0, "next_num": 82401,
         "accounts": [{"email": "komex82398@duidir.com", "password": "komex82398@duidir.com"},
                      {"email": "komex82400@duidir.com", "password": "komex82400@duidir.com"}],
         "limits": {}, "signups": {"date": "", "n": 0}}
_CA_SYNC = {"t": 0.0}
# کاتالۆگی بنەڕەتی — sync ی خۆکار لە HTML ی ماڵپەر نوێی دەکاتەوە (key → version, label)
CA_FALLBACK = {
    "gpt-5.4-nano": ("gpt-5.4-nano", "GPT-5.4 Nano"),
    "gpt-5.4-instant": ("gpt-5.4-instant-2026-03-05", "GPT-5.4 Instant"),
    "gemini-3.1-pro": ("gemini-3.1-pro-preview", "Gemini 3.1 Pro"),
    "claude": ("claude-sonnet-5", "Claude Sonnet 5"),
    "perplexity": ("sonar", "Perplexity"),
    "deepseek": ("deepseek-4-pro-0813", "DeepSeek-V4-Pro"),
    "grok": ("grok-4.6", "Grok 4.6"),
    "claude-fable": ("claude-fable-5-1", "Claude Fable 5.1"),
    "claude-opus": ("claude-opus-5", "Claude Opus 5"),
    "gemini": ("gemini-3.8-flash", "Gemini 3.8 Flash"),
    "gpt-5.6-sol": ("gpt-5.6-sol", "GPT-5.6 Sol"),
    "gpt-5.6-terra": ("gpt-5.6-terra", "GPT-5.6 Terra"),
    "gpt-5.6-luna": ("gpt-5.6-luna", "GPT-5.6 Luna"),
    "gpt-6-astra": ("gpt-6-astra", "GPT-6 Astra"),
    "gpt-5.5": ("gpt-5.5-2026-04-23", "GPT-5.5"),
    "kimi": ("kimi-k3", "Kimi K3"),
    "kimi-k2.6": ("kimi-k2.6", "Kimi K2.6"),
    "kimi-k3-thinking": ("kimi-k3-thinking", "Kimi K3 Thinking"),
    "deepseek-v4-pro-thinking": ("deepseek-4-pro-0813-thinking", "DeepSeek-V4-Pro Thinking"),
    "o3": ("o3-2025-04-16", "OpenAI o3"),
    "llama": ("llama-4-maverick", "Llama 4"),
    "gpt-4": ("gpt-4o-2024-08-06", "GPT-4o"),
    "gpt-4o-mini": ("gpt-4o-mini-2024-07-18", "GPT-4o-mini"),
    "gpt-4.1": ("gpt-4.1-2025-04-14", "GPT-4.1"),
}


def _ca_load_acc():
    import json as _j
    try:
        d = _j.load(open(CA_ACC_FILE, encoding="utf-8"))
        CA_ST["accounts"] = d.get("accounts") or CA_ST["accounts"]
        CA_ST["idx"] = int(d.get("idx") or 0)
        CA_ST["next_num"] = int(d.get("next_num") or 82401)
        CA_ST["limits"] = d.get("limits") or {}
        CA_ST["signups"] = d.get("signups") or {"date": "", "n": 0}
    except Exception:
        pass


def _ca_save_acc():
    import json as _j
    try:
        _j.dump({"accounts": CA_ST.get("accounts") or [], "idx": CA_ST["idx"],
                 "next_num": CA_ST["next_num"], "limits": CA_ST.get("limits") or {},
                 "signups": CA_ST.get("signups") or {"date": "", "n": 0}},
                open(CA_ACC_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


_ca_load_acc()


def _ca_firebase(ep, email, pw):
    r = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:{ep}?key={CA_KEY}",
                      json={"email": email, "password": pw, "returnSecureToken": True},
                      headers={"User-Agent": CA_UA}, timeout=(10, 25))
    if r.status_code != 200:
        return None
    tok = (r.json() or {}).get("idToken")
    return (tok, "") if tok else None


def _ca_signup_new():
    import datetime as _dt
    today = _dt.datetime.utcnow().strftime("%Y-%m-%d")
    sg = CA_ST.get("signups") or {"date": "", "n": 0}
    if sg.get("date") != today:
        sg = {"date": today, "n": 0}
    if sg.get("n", 0) >= 20 or len(CA_ST.get("accounts") or []) >= 40:
        return None
    n = CA_ST["next_num"]
    for _ in range(6):
        email = f"komex{n}@duidir.com"
        res = _ca_firebase("signUp", email, email)
        if res:
            CA_ST["accounts"] = (CA_ST.get("accounts") or []) + [{"email": email, "password": email}]
            CA_ST["idx"] = len(CA_ST["accounts"]) - 1
            CA_ST["next_num"] = n + 1
            sg["n"] = sg.get("n", 0) + 1
            CA_ST["signups"] = sg
            CA_ST["tok"] = None
            _ca_save_acc()
            print(f"[CA] ئەکاونتی نوێ ✅ {email}", flush=True)
            return res
        n += 1
    CA_ST["next_num"] = n
    _ca_save_acc()
    return None


def _ca_token():
    import time as _t
    if CA_ST.get("tok") and _t.time() - CA_ST.get("tok_t", 0) < 2700:
        return CA_ST["tok"]
    accs = CA_ST.get("accounts") or []
    if accs:
        acc = accs[CA_ST["idx"] % len(accs)]
        res = _ca_firebase("signInWithPassword", acc["email"], acc["password"])
        if res:
            CA_ST["tok"] = res[0]
            CA_ST["tok_t"] = _t.time()
            return CA_ST["tok"]
    resn = _ca_signup_new()
    if not resn:
        raise EMError("ca: هیچ ئەکاونت")
    CA_ST["tok"] = resn[0]
    CA_ST["tok_t"] = _t.time()
    return CA_ST["tok"]


def _ca_rotate(model_key):
    """ئەکاونتی دواتر بۆ ئەم مۆدێڵە — ئەوانەی سنووریان تێپەڕاندووە لابەرە؛ ئەگەر نەمابوو → نوێ"""
    accs = CA_ST.get("accounts") or []
    lim = CA_ST.get("limits") or {}
    for _ in range(len(accs)):
        CA_ST["idx"] = (CA_ST["idx"] + 1) % len(accs)
        acc = accs[CA_ST["idx"]]
        em = lim.get(acc["email"]) or {}
        if not em.get(model_key) and not em.get("*"):
            CA_ST["tok"] = None
            _ca_save_acc()
            return True
    return bool(_ca_signup_new())


def _ca_models_catalog():
    cat = {}
    for k, v in (MS.get("ca_ok") or {}).items():
        cat[k] = (v.get("version") or k, v.get("label") or k)
    for k, v in CA_FALLBACK.items():
        cat.setdefault(k, v)
    return cat


def ca_chat(messages, model_id, timeout=110):
    """چاتی ChatbotAI — send + پۆڵی get-all + حەوزی ئەکاونت + خۆکار-ساینئەپ"""
    import time as _t
    cat = _ca_models_catalog()
    if model_id not in cat:
        raise EMError("ca: مۆدێڵ نییە")
    mkey, mver = model_id, cat[model_id][0]
    lines = []
    for m in messages[-12:]:
        role = m.get("role")
        c = (m.get("content") or "").strip()
        if not c:
            continue
        if role == "system":
            lines.append("[Instructions] " + c)
        elif role == "user":
            lines.append("[User] " + c)
        else:
            lines.append("[Assistant] " + c)
    if not lines:
        raise EMError("ca: هیچ نامە")
    lines.append("[Assistant]")
    prompt = "\n".join(lines)[-6000:]
    last_err = ""
    for attempt in range(8):
        try:
            tok = _ca_token()
        except EMError:
            if not _ca_rotate(mkey):
                raise
            continue
        H = {"User-Agent": CA_UA, "Content-Type": "application/json",
             "authorization": tok, "Origin": CA_BASE, "Referer": CA_BASE + "/"}
        try:
            r = requests.post(CA_BASE + "/api/chat/message/send",
                              json={"message": prompt, "model": mkey, "temporaryChat": False,
                                    "modelVersion": mver}, headers=H, timeout=(15, 40))
        except Exception as e:
            raise EMError(f"ca: {str(e)[:60]}")
        ok = False
        sid = ""
        err = ""
        try:
            j = r.json() or {}
            ok = bool(j.get("success"))
            sid = str(j.get("sessionId") or "")
            err = str(j.get("error") or "")
        except Exception:
            err = r.text[:80]
        if not ok:
            last_err = err or str(r.status_code)
            low = last_err.lower()
            if "limit" in low or "free message" in low or "no free" in low:
                accs = CA_ST.get("accounts") or []
                if accs:
                    acc = accs[CA_ST["idx"] % len(accs)]
                    lm = CA_ST.setdefault("limits", {}).setdefault(acc["email"], {})
                    lm[mkey] = True
                    if "lifetime" not in low:
                        lm["*"] = True  # ئەژمێرەکە بە گشتی تەواوە
                    _ca_save_acc()
                if not _ca_rotate(mkey):
                    raise EMError("ca: سنووری هەموو ئەکاونتەکان")
                continue
            if r.status_code in (401, 403):
                CA_ST["tok"] = None
                if not _ca_rotate(mkey):
                    raise EMError("ca: توکن")
                continue
            raise EMError(f"ca: {last_err[:60]}")
        # پۆڵی وەڵام — get-all (POST)
        deadline = _t.time() + min(timeout, 100)
        while _t.time() < deadline:
            _t.sleep(2.5)
            try:
                r2 = requests.post(CA_BASE + "/api/session/get-all", headers=H, json={}, timeout=(15, 30))
                sessions = (r2.json() or {}).get("sessions") or []
            except Exception:
                continue
            for s in sessions:
                if str(s.get("sessionId")) != sid:
                    continue
                ms = s.get("messages") or []
                if ms and ms[-1].get("finish_reason") == "stop":
                    ans = (ms[-1].get("content") or "").strip()
                    if ans:
                        return ans
        last_err = "بەتاڵ/درەنگ"
        CA_ST["tok"] = None
    raise EMError(f"ca: {last_err[:60] or 'شکست'}")


def ca_servers():
    src = MS.get("ca_ok") or {k: {"version": v[0], "label": v[1]} for k, v in CA_FALLBACK.items()}
    out = []
    for k in sorted(src):
        lbl = (src[k] or {}).get("label") or k
        out.append({"id": f"ca-{re.sub(r'[^a-z0-9]+', '-', k.lower()).strip('-')}",
                    "name": f"{lbl} (CA)", "model_id": k, "kind": "ca"})
    return out


def _ca_extract_models(html):
    """نەخشەی مۆدێڵەکان لە payload ی Nuxt ی HTML — کۆنفیگی multi_language (idMap: نرخ لە شوێنی تر)"""
    i = 0
    while True:
        j = -1
        for pat in ('{\\\\"is_active', '{\\"is_active', '{"is_active'):
            j = html.find(pat, i)
            if j >= 0:
                break
        if j < 0:
            return None
        k = html.rfind('"', max(0, j - 8), j)
        if k < 0:
            i = j + 1
            continue
        out = []
        esc = False
        pos = k + 1
        while pos < len(html):
            ch = html[pos]
            if esc:
                out.append(ch)
                esc = False
            elif ch == "\\":
                out.append(ch)
                esc = True
            elif ch == '"':
                break
            else:
                out.append(ch)
            pos += 1
        i = pos + 1
        try:
            inner = json.loads('"' + "".join(out) + '"')
            cfg = json.loads(inner)
        except Exception:
            continue
        if isinstance(cfg, dict) and isinstance(cfg.get("models"), dict) and len(cfg["models"]) >= 3:
            return cfg["models"]
    return None


def sync_ca_models(force=False):
    """ئۆتۆ-ئەپدێتی ChatbotAI: نەخشەی مۆدێڵەکان لە HTML ی /chat — ٦ کاتژمێر"""
    import time as _t
    if not force and _t.time() - _CA_SYNC["t"] < 21600:
        return
    _CA_SYNC["t"] = _t.time()
    try:
        r = requests.get(CA_BASE + "/chat", headers={"User-Agent": CA_UA, "Accept": "text/html",
                                                     "Referer": CA_BASE + "/"}, timeout=(15, 40))
        if r.status_code != 200:
            print(f"[CA-SYNC] HTML {r.status_code}", flush=True)
            return
        models = _ca_extract_models(r.text)
        if not models:
            print("[CA-SYNC] نەخشە نەدۆزرایەوە — کاتی کۆن دەمێنێتەوە", flush=True)
            return
        ok = {}
        for k, v in models.items():
            try:
                if not (v or {}).get("is_active"):
                    continue
                ok[k] = {"version": v.get("version") or k, "label": v.get("display_name") or k}
            except Exception:
                continue
        if len(ok) >= 5:
            MS["ca_ok"] = ok
            _ms_save()
            print(f"[CA-SYNC] کاتالۆگ {len(ok)} مۆدێڵ", flush=True)
    except Exception as e:
        print(f"[CA-SYNC] {str(e)[:80]}", flush=True)


# ══════════ AskAI (askaichat.app) — §2.31 — Firebase + cerebroId + حەوزی ئەکاونت + خۆکار-ساینئەپ ══════════
AC_KEY = "AIzaSyBIjexOfpMhsws3weHS6Hko4d5Arin3Zzs"
AC_BASE = "https://askaichat.app"
AC_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
AC_ACC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ac_accounts.json")
AC_ST = {"tok": None, "tok_t": 0.0, "idx": 0, "next_num": 82407,
         "accounts": [{"email": "komex82398@duidir.com", "password": "komex82398@duidir.com"},
                      {"email": "komex82406@duidir.com", "password": "komex82406@duidir.com"}],
         "limits": {}, "signups": {"date": "", "n": 0}}
_AC_SYNC = {"t": 0.0}
# کاتالۆگی بنەڕەتی — تەنها ئەوانەی سنووری خۆڕاییان هەیە (چاکەکان limit=0 ئەنجام نادەن)
AC_FALLBACK = {
    "gpt-5.4-nano": ("gpt-5.4-nano", "GPT-5.4 Nano"),
}


def _ac_load_acc():
    import json as _j
    try:
        d = _j.load(open(AC_ACC_FILE, encoding="utf-8"))
        AC_ST["accounts"] = d.get("accounts") or AC_ST["accounts"]
        AC_ST["idx"] = int(d.get("idx") or 0)
        AC_ST["next_num"] = int(d.get("next_num") or 82407)
        AC_ST["limits"] = d.get("limits") or {}
        AC_ST["signups"] = d.get("signups") or {"date": "", "n": 0}
    except Exception:
        pass


def _ac_save_acc():
    import json as _j
    try:
        _j.dump({"accounts": AC_ST.get("accounts") or [], "idx": AC_ST["idx"],
                 "next_num": AC_ST["next_num"], "limits": AC_ST.get("limits") or {},
                 "signups": AC_ST.get("signups") or {"date": "", "n": 0}},
                open(AC_ACC_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


_ac_load_acc()


def _ac_firebase(ep, email, pw):
    r = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:{ep}?key={AC_KEY}",
                      json={"email": email, "password": pw, "returnSecureToken": True},
                      headers={"User-Agent": AC_UA}, timeout=(10, 25))
    if r.status_code != 200:
        return None
    j = r.json() or {}
    tok = j.get("idToken")
    if not tok:
        return None
    return tok, j.get("localId") or ""


def _ac_bootstrap(tok, uid, email):
    """پرۆفایلی cerebro + user/set بە cerebroId — بەبێ ئەمە نەوەکە ناگوزەرێت"""
    import random as _r, string as _s
    cid = "web_" + "".join(_r.choices(_s.ascii_letters + _s.digits, k=9))
    try:
        requests.post("https://gateway.cerebroapi.com/user/web",
                      json={"user_id": cid, "app_id": "com.codeway.chatappweb", "version": "1.0.0",
                            "operating_system": "Windows", "properties": {"userAgent": AC_UA}},
                      headers={"User-Agent": AC_UA}, timeout=(10, 20))
    except Exception:
        pass
    import time as _t
    try:
        requests.post(AC_BASE + "/api/user/set",
                      json={"userId": uid, "firebaseUserId": uid, "email": email,
                            "createdAt": int(_t.time() * 1000), "cerebroId": cid,
                            "providerData": [{"providerId": "password", "uid": email, "displayName": None,
                                              "email": email, "phoneNumber": None, "photoURL": None}],
                            "originOnboarding": "Home", "emailConsent": True,
                            "temporaryChatOnboarding": True},
                      headers={"authorization": tok, "User-Agent": AC_UA, "Origin": AC_BASE,
                               "Referer": AC_BASE + "/", "Content-Type": "application/json"},
                      timeout=(10, 25))
    except Exception:
        pass


def _ac_signup_new():
    import datetime as _dt
    today = _dt.datetime.utcnow().strftime("%Y-%m-%d")
    sg = AC_ST.get("signups") or {"date": "", "n": 0}
    if sg.get("date") != today:
        sg = {"date": today, "n": 0}
    if sg.get("n", 0) >= 20 or len(AC_ST.get("accounts") or []) >= 40:
        return None
    n = AC_ST["next_num"]
    for _ in range(6):
        email = f"komex{n}@duidir.com"
        res = _ac_firebase("signUp", email, email)
        if res:
            acc = {"email": email, "password": email, "boot": True}
            try:
                _ac_bootstrap(res[0], res[1], email)
            except Exception:
                pass
            AC_ST["accounts"] = (AC_ST.get("accounts") or []) + [acc]
            AC_ST["idx"] = len(AC_ST["accounts"]) - 1
            AC_ST["next_num"] = n + 1
            sg["n"] = sg.get("n", 0) + 1
            AC_ST["signups"] = sg
            AC_ST["tok"] = None
            _ac_save_acc()
            print(f"[AC] ئەکاونتی نوێ ✅ {email}", flush=True)
            return res
        n += 1
    AC_ST["next_num"] = n
    _ac_save_acc()
    return None


def _ac_token():
    import time as _t
    if AC_ST.get("tok") and _t.time() - AC_ST.get("tok_t", 0) < 2700:
        return AC_ST["tok"]
    accs = AC_ST.get("accounts") or []
    if accs:
        acc = accs[AC_ST["idx"] % len(accs)]
        res = _ac_firebase("signInWithPassword", acc["email"], acc["password"])
        if res:
            AC_ST["tok"] = res[0]
            AC_ST["tok_t"] = _t.time()
            if not acc.get("boot"):
                try:
                    _ac_bootstrap(res[0], res[1], acc["email"])
                except Exception:
                    pass
                acc["boot"] = True
                _ac_save_acc()
            return AC_ST["tok"]
    resn = _ac_signup_new()
    if not resn:
        raise EMError("ac: هیچ ئەکاونت")
    AC_ST["tok"] = resn[0]
    AC_ST["tok_t"] = _t.time()
    return AC_ST["tok"]


def _ac_rotate(model_key):
    accs = AC_ST.get("accounts") or []
    lim = AC_ST.get("limits") or {}
    for _ in range(len(accs)):
        AC_ST["idx"] = (AC_ST["idx"] + 1) % len(accs)
        acc = accs[AC_ST["idx"]]
        em = lim.get(acc["email"]) or {}
        if not em.get(model_key) and not em.get("*"):
            AC_ST["tok"] = None
            _ac_save_acc()
            return True
    return bool(_ac_signup_new())


def _ac_catalog():
    cat = {}
    for k, v in (MS.get("ac_ok") or {}).items():
        cat[k] = (v.get("version") or k, v.get("label") or k)
    for k, v in AC_FALLBACK.items():
        cat.setdefault(k, v)
    return cat


def ac_chat(messages, model_id, timeout=110):
    """چاتی AskAI — send + SSE stream ی session + حەوزی ئەکاونت + خۆکار-ساینئەپ"""
    import time as _t
    cat = _ac_catalog()
    if model_id not in cat:
        raise EMError("ac: مۆدێڵ نییە")
    mkey, mver = model_id, cat[model_id][0]
    lines = []
    for m in messages[-12:]:
        role = m.get("role")
        c = (m.get("content") or "").strip()
        if not c:
            continue
        if role == "system":
            lines.append("[Instructions] " + c)
        elif role == "user":
            lines.append("[User] " + c)
        else:
            lines.append("[Assistant] " + c)
    if not lines:
        raise EMError("ac: هیچ نامە")
    lines.append("[Assistant]")
    prompt = "\n".join(lines)[-6000:]
    last_err = ""
    for attempt in range(8):
        try:
            tok = _ac_token()
        except EMError:
            if not _ac_rotate(mkey):
                raise
            continue
        H = {"User-Agent": AC_UA, "Content-Type": "application/json", "authorization": tok,
             "Origin": AC_BASE, "Referer": AC_BASE + "/", "accept": "text/event-stream"}
        try:
            r = requests.post(AC_BASE + "/api/chat/message/send",
                              json={"message": prompt, "model": mkey, "temporaryChat": False,
                                    "modelVersion": mver}, headers=H, timeout=(15, 40))
        except Exception as e:
            raise EMError(f"ac: {str(e)[:60]}")
        ok = False
        sid = ""
        err = ""
        try:
            j = r.json() or {}
            ok = bool(j.get("success"))
            sid = str(j.get("sessionId") or "")
            err = str(j.get("error") or "")
        except Exception:
            err = r.text[:80]
        if not ok:
            last_err = err or str(r.status_code)
            low = last_err.lower()
            if "limit" in low or "free message" in low or "no free" in low:
                accs = AC_ST.get("accounts") or []
                if accs:
                    acc = accs[AC_ST["idx"] % len(accs)]
                    lm = AC_ST.setdefault("limits", {}).setdefault(acc["email"], {})
                    lm[mkey] = True
                    if "lifetime" not in low:
                        lm["*"] = True
                    _ac_save_acc()
                if not _ac_rotate(mkey):
                    raise EMError("ac: سنووری هەموو ئەکاونتەکان")
                continue
            if r.status_code in (401, 403):
                AC_ST["tok"] = None
                if not _ac_rotate(mkey):
                    raise EMError("ac: توکن")
                continue
            raise EMError(f"ac: {last_err[:60]}")
        # SSE stream — snapshot ی نشست
        ans = ""
        deadline = _t.time() + min(timeout, 100)
        try:
            r2 = requests.get(AC_BASE + "/api/session/stream",
                              params={"sessionId": sid, "isTool": "false", "isAssistant": "false"},
                              headers=H, timeout=(15, 100), stream=True)
            for line in r2.iter_lines(decode_unicode=True):
                if _t.time() > deadline:
                    break
                if not line or not line.startswith("data:"):
                    continue
                try:
                    d = json.loads(line[5:].strip())
                except Exception:
                    continue
                if d.get("type") != "snapshot":
                    continue
                data = d.get("data") or {}
                ms = data.get("messages") or []
                am = [x for x in ms if x.get("role") == "assistant"]
                if am and data.get("status") == "completed":
                    ans = (am[-1].get("message") or "").strip()
                    break
            try:
                r2.close()
            except Exception:
                pass
        except Exception as e:
            last_err = str(e)[:60]
            AC_ST["tok"] = None
            continue
        if ans:
            return ans
        last_err = "بەتاڵ/درەنگ"
        AC_ST["tok"] = None
    raise EMError(f"ac: {last_err[:60] or 'شکست'}")


def ac_servers():
    src = MS.get("ac_ok") or {k: {"version": v[0], "label": v[1]} for k, v in AC_FALLBACK.items()}
    out = []
    for k in sorted(src):
        lbl = (src[k] or {}).get("label") or k
        out.append({"id": f"ac-{re.sub(r'[^a-z0-9]+', '-', k.lower()).strip('-')}",
                    "name": f"{lbl} (AC)", "model_id": k, "kind": "ac"})
    return out


def sync_ac_models(force=False):
    """ئۆتۆ-ئەپدێتی AskAI: نەخشەی مۆدێڵەکان لە HTML — ٦ کاتژمێر (هەمان پارسەری Nuxt)"""
    import time as _t
    if not force and _t.time() - _AC_SYNC["t"] < 21600:
        return
    _AC_SYNC["t"] = _t.time()
    try:
        r = requests.get(AC_BASE + "/chat", headers={"User-Agent": AC_UA, "Accept": "text/html",
                                                     "Referer": AC_BASE + "/"}, timeout=(15, 40))
        if r.status_code != 200:
            print(f"[AC-SYNC] HTML {r.status_code}", flush=True)
            return
        models = _ca_extract_models(r.text)
        if not models:
            print("[AC-SYNC] نەخشە نەدۆزرایەوە — کاتی کۆن دەمێنێتەوە", flush=True)
            return
        ok = {}
        for k, v in models.items():
            try:
                if not (v or {}).get("is_active"):
                    continue
                # تەنها ئەوانەی سنووری خۆڕاییان هەیە — ئەوانی تر پرۆن و هەمیشە شکست دەخۆن
                if not (v.get("free_lifetime_message_limit") or 0) > 0:
                    continue
                ok[k] = {"version": v.get("version") or k, "label": v.get("display_name") or k}
            except Exception:
                continue
        if len(ok) >= 1:
            MS["ac_ok"] = ok
            _ms_save()
            print(f"[AC-SYNC] کاتالۆگ {len(ok)} مۆدێڵی خۆڕایی", flush=True)
    except Exception as e:
        print(f"[AC-SYNC] {str(e)[:80]}", flush=True)


# ══════════ Nova (chat.novaapp.ai) — §2.32 — Firebase + حەوزی ئەکاونت + خۆکار-ساینئەپ ══════════
NV_KEY = "AIzaSyAOuqWxL44t4n0_uF00qj7jh8kmb8Ly9s0"
NV_BASE = "https://api.novaapp.ai"
NV_CMS = "https://webcms.novaapp.ai/api/ai-models?populate[]=tags&populate[]=examples&populate[]=suggestions&pagination[pageSize]=100"
NV_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
NV_ACC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nv_accounts.json")
NV_ST = {"tok": None, "uid": None, "tok_t": 0.0, "idx": 0, "next_num": 82416,
         "accounts": [{"email": "komex82398@duidir.com", "password": "komex82398@duidir.com"},
                      {"email": "komex82414@duidir.com", "password": "komex82414@duidir.com"},
                      {"email": "komex82415@duidir.com", "password": "komex82415@duidir.com"}],
         "exhausted": {}, "ensured": {}, "signups": {"date": "", "n": 0}}
_NV_SYNC = {"t": 0.0}
# مۆدێڵی هەرزان — بە botId دەناسرێتەوە (کاتالۆگ بە modelKey دەگۆڕدرێت بەڵام botId جێگیرە)
NV_FREE_BOTS = {0: "4o-mini", 9: "auto", 10: "gemini-2.5-flash", 15: "claude", 21: "deepSeek",
                26: "gpt-4.1", 44: "claude-4.5-haiku", 49: "gpt-5.1", 100: "gemini-3-flash",
                108: "gpt-5.6-luna", 111: "deepseek-v4-flash"}
# پرێمیۆم — ensure-credits کرێدیتی دەستپێک دەدات؛ تەنها هەرزانەکان (28/29) بە ڕۆتەیشن دەکرێنەوە
NV_PREM_CHEAP = {28, 29}
NV_PREMIUM_BOTS = {14: "deepSeekV4", 28: "gpt-5", 29: "gpt-5-mini", 40: "o3", 46: "claude-4.5-sonnet",
                   50: "gemini-3.1-pro", 106: "gpt-5.5", 107: "gpt-5.4", 110: "claude-4.6-sonnet",
                   112: "deepseek-v4-pro", 113: "grok-4.3", 114: "gemini-3.1-flash-lite", 115: "gpt-5.3",
                   116: "gpt-5.6", 117: "claude-5-sonnet", 119: "claude-5-opus", 120: "grok-4.5",
                   121: "gemini-3.6-flash", 122: "gpt-5.6-terra", 123: "gemini-3-pro", 125: "claude-4.6-opus",
                   126: "claude-4.8-opus", 127: "grok-4.20", 128: "claude-5-fable", 136: "gpt-6-astra"}
NV_HTTP400_BOTS = {5, 23, 45, 201, 403}  # پێویستیان بە پارامەتری جیاواز — هێشتا ناتۆمارکرێن
NV_PREF = {0: "4o-mini", 108: "gpt-5.6-luna", 14: "deepSeekV4", 107: "gpt-5.4", 110: "claude-4.6-sonnet",
           115: "gpt-5.3", 123: "gemini-3-pro", 128: "claude-5-fable"}
NV_SKIP_KEYS = {"link-and-ask", "music-generation", "document", "editor", "ai-search", "superbot", "aiapp", "chatbotapp", "youtube-summarizer", "image-generator", "logo-generator", "tattoo-generator", "nova"}


def _nv_load_acc():
    import json as _j
    try:
        d = _j.load(open(NV_ACC_FILE, encoding="utf-8"))
        NV_ST["accounts"] = d.get("accounts") or NV_ST["accounts"]
        NV_ST["idx"] = int(d.get("idx") or 0)
        NV_ST["next_num"] = int(d.get("next_num") or 82416)
        NV_ST["exhausted"] = d.get("exhausted") or {}
        NV_ST["ensured"] = d.get("ensured") or {}
        NV_ST["signups"] = d.get("signups") or {"date": "", "n": 0}
    except Exception:
        pass


def _nv_save_acc():
    import json as _j
    try:
        _j.dump({"accounts": NV_ST.get("accounts") or [], "idx": NV_ST["idx"],
                 "next_num": NV_ST["next_num"], "exhausted": NV_ST.get("exhausted") or {},
                 "ensured": NV_ST.get("ensured") or {},
                 "signups": NV_ST.get("signups") or {"date": "", "n": 0}},
                open(NV_ACC_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


_nv_load_acc()


def _nv_firebase(ep, email, pw):
    r = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:{ep}?key={NV_KEY}",
                      json={"email": email, "password": pw, "returnSecureToken": True},
                      headers={"User-Agent": NV_UA}, timeout=(10, 25))
    if r.status_code != 200:
        return None
    j = r.json() or {}
    tok = j.get("idToken")
    if not tok:
        return None
    return tok, j.get("localId") or ""


def _nv_signup_new():
    import datetime as _dt
    today = _dt.datetime.utcnow().strftime("%Y-%m-%d")
    sg = NV_ST.get("signups") or {"date": "", "n": 0}
    if sg.get("date") != today:
        sg = {"date": today, "n": 0}
    if sg.get("n", 0) >= 24 or len(NV_ST.get("accounts") or []) >= 60:
        return None
    import time as _ts
    n = NV_ST["next_num"]
    for attempt in range(2):
        for _ in range(6):
            email = f"komex{n}@duidir.com"
            res = _nv_firebase("signUp", email, email)
            if res:
                NV_ST["accounts"] = (NV_ST.get("accounts") or []) + [{"email": email, "password": email}]
                NV_ST["idx"] = len(NV_ST["accounts"]) - 1
                NV_ST["next_num"] = n + 1
                sg["n"] = sg.get("n", 0) + 1
                NV_ST["signups"] = sg
                NV_ST["tok"] = None
                _nv_save_acc()
                print(f"[NV] ئەکاونتی نوێ ✅ {email}", flush=True)
                return res
            n += 1
            _ts.sleep(1.5)
        NV_ST["next_num"] = n
        if attempt == 0:
            _ts.sleep(5)  # rate-limit — دووبارە
    _nv_save_acc()
    return None


def _nv_token():
    import time as _t
    if NV_ST.get("tok") and NV_ST.get("uid") and _t.time() - NV_ST.get("tok_t", 0) < 2700:
        return NV_ST["tok"], NV_ST["uid"]
    accs = NV_ST.get("accounts") or []
    if accs:
        acc = accs[NV_ST["idx"] % len(accs)]
        res = _nv_firebase("signInWithPassword", acc["email"], acc["password"])
        if res:
            NV_ST["tok"], NV_ST["uid"] = res
            NV_ST["tok_t"] = _t.time()
            return res
    resn = _nv_signup_new()
    if not resn:
        raise EMError("nv: هیچ ئەکاونت")
    NV_ST["tok"], NV_ST["uid"] = resn
    NV_ST["tok_t"] = _t.time()
    return resn


def _nv_rotate():
    import time as _ts
    accs = NV_ST.get("accounts") or []
    if not accs:
        return bool(_nv_signup_new())
    ex = NV_ST.get("exhausted") or {}
    now = _ts.time()
    for _ in range(len(accs)):
        NV_ST["idx"] = (NV_ST["idx"] + 1) % len(accs)
        acc = accs[NV_ST["idx"]]
        if float(ex.get(acc["email"], 0)) > now:
            continue  # هێشتا سارد نەبووەتەوە (کۆڵ ٦٠٠ چرکە)
        NV_ST["tok"] = None
        _nv_save_acc()
        return True
    res = _nv_signup_new()
    if res:
        return True
    # فەرموودەی کۆتایی — ئەگەر ساینئەپ شکست خوارد، هەر ئەکاونتێک (تەنانەت ساردبوو)
    NV_ST["idx"] = (NV_ST["idx"] + 1) % len(accs)
    NV_ST["tok"] = None
    _nv_save_acc()
    return True


def nv_chat(messages, model_id, timeout=110):
    """چاتی Nova — هەمان فلۆوی §2.29 + حەوزی ئەکاونت (٥ نامەی خۆڕایی/ئەکاونت)"""
    import time as _t, uuid as _u
    meta = (MS.get("nv_ok") or {}).get(model_id)
    if not meta:
        raise EMError("nv: مۆدێڵ نییە")
    bot_id = meta.get("botId") or 0
    tier = meta.get("tier") or "f"
    max_att = 3 if tier == "p" else (1 if tier == "x" else 8)
    lines = []
    for m in messages[-12:]:
        role = m.get("role")
        c = (m.get("content") or "").strip()
        if not c:
            continue
        if role == "system":
            lines.append("[Instructions] " + c)
        elif role == "user":
            lines.append("[User] " + c)
        else:
            lines.append("[Assistant] " + c)
    if not lines:
        raise EMError("nv: هیچ نامە")
    lines.append("[Assistant]")
    prompt = "\n".join(lines)[-6000:]
    last_err = ""
    import datetime as _dtm
    _today = _dtm.datetime.utcnow().strftime("%Y-%m-%d")
    for attempt in range(max_att):
        try:
            tok, uid = _nv_token()
        except EMError:
            if not _nv_rotate():
                raise
            continue
        H = {"User-Agent": NV_UA, "Content-Type": "application/json", "accept": "text/event-stream",
             "X_Token": tok, "X_User_Id": uid, "X_Platform": "web", "X_Model": str(bot_id),
             "Origin": "https://chat.novaapp.ai", "Referer": "https://chat.novaapp.ai/"}
        if tier in ("p", "x"):
            accs0 = NV_ST.get("accounts") or []
            em0 = accs0[NV_ST["idx"] % len(accs0)]["email"] if accs0 else ""
            en = NV_ST.setdefault("ensured", {})
            if en.get(em0) != _today:
                try:
                    requests.get(NV_BASE + "/api/v2/ensure-credits",
                                 headers={"User-Agent": NV_UA, "X_Token": tok, "X_User_Id": uid,
                                          "X_Platform": "web", "Origin": "https://chat.novaapp.ai",
                                          "Referer": "https://chat.novaapp.ai/"}, timeout=(10, 20))
                except Exception:
                    pass
                en[em0] = _today
                _nv_save_acc()
        body = {"botId": bot_id, "sessionId": _u.uuid4().hex[:20],
                "userPseudoId": f"{_u.uuid4().int % 10 ** 9}.{int(_t.time())}",
                "hubxId": str(_u.uuid4()),
                "message": {"prompt": prompt, "messageId": str(_u.uuid4())},
                "actions": {"webSearch": False, "createImage": False, "deepSearch": False, "privateSearch": False}}
        try:
            r = requests.post(NV_BASE + "/api/v2/chat", json=body, headers=H,
                              timeout=(15, timeout), stream=True)
        except Exception as e:
            raise EMError(f"nv: {str(e)[:60]}")
        if r.status_code != 200:
            raw = b""
            try:
                for ch in r.iter_content(chunk_size=None):
                    raw += ch
                    if len(raw) > 300:
                        break
            except Exception:
                pass
            msg = ""
            try:
                msg = (json.loads(raw.decode("utf-8", "replace")).get("data") or {}).get("message", "")
            except Exception:
                msg = raw[:60].decode("utf-8", "replace")
            last_err = msg or str(r.status_code)
            if "Insufficient chat credit" in msg:
                if tier == "x":
                    raise EMError("nv: پرێمیۆمی-قورس — بە پارە بەردەستە")
                accs = NV_ST.get("accounts") or []
                if accs:
                    acc = accs[NV_ST["idx"] % len(accs)]
                    NV_ST.setdefault("exhausted", {})[acc["email"]] = _t.time() + 600  # کۆڵ ١٠ خولەک
                if not _nv_rotate():
                    raise EMError("nv: حەوزی ئەکاونتەکان تەواوە")
                _t.sleep(1.5)
                continue
            if "No agent mapping" in msg:
                MS.setdefault("nv_bad", {})[model_id] = {"t": _t.time(), "why": "no-mapping"}
                MS.get("nv_ok", {}).pop(model_id, None)
                _ms_save()
                raise EMError("nv: مۆدێڵ نەماوە")
            raise EMError(f"nv: {last_err[:60]}")
        parts = []
        for line in r.iter_lines(decode_unicode=True):
            if not line.startswith("data:"):
                continue
            try:
                d = json.loads(line[5:].strip())
            except Exception:
                continue
            dd = d.get("data") or {}
            if isinstance(dd, dict):
                c = dd.get("content")
                if isinstance(c, dict) and c.get("parts"):
                    for p in c["parts"]:
                        if isinstance(p, dict) and p.get("thought"):
                            continue  # پارچەی بیرکردنەوە — فڕێدان
                        parts.append((p or {}).get("text", "") if isinstance(p, dict) else str(p))
        if not parts:
            NV_ST["tok"] = None
            last_err = "بەتاڵ"
            continue
        # پترن: دێڵتا زیادەکان + لە کۆتایی ڕووداوی کۆتایی-کۆکراو
        if len(parts) > 1 and parts[-1].startswith("".join(parts[:-1])):
            ans = parts[-1].strip()
        else:
            ans = "".join(parts).strip()
        if ans:
            return ans
        last_err = "بەتاڵ"
        NV_ST["tok"] = None
    raise EMError(f"nv: {last_err[:60] or 'شکست'}")


def nv_servers():
    out = []
    for k, meta in sorted((MS.get("nv_ok") or {}).items()):
        out.append({"id": f"nv-{re.sub(r'[^a-z0-9]+', '-', str(k).lower()).strip('-') or 'model'}",
                    "name": f"{(meta or {}).get('label') or k} (NV)", "model_id": k, "kind": "nv"})
    return out


def sync_nv_models(force=False):
    """ئۆتۆ-ئەپدێتی Nova: کاتالۆگی webcms — تەنها مۆدێڵی هەرزان (botId ∈ NV_FREE_BOTS)"""
    import time as _t
    if not force and _t.time() - _NV_SYNC["t"] < 21600:
        return
    _NV_SYNC["t"] = _t.time()
    try:
        r = requests.get(NV_CMS, headers={"User-Agent": NV_UA, "Origin": "https://chat.novaapp.ai",
                                          "Referer": "https://chat.novaapp.ai/"}, timeout=(10, 40))
        if r.status_code != 200:
            print(f"[NV-SYNC] catalog {r.status_code}", flush=True)
            return
        items = (r.json() or {}).get("data") or []
        ok = {}
        for m in items:
            k = (m or {}).get("modelKey") or ""
            b = m.get("botId")
            if not k or k in NV_SKIP_KEYS or b is None:
                continue
            if (m.get("type") or "") != "text":
                continue
            # هەموو مۆدێڵێک — یەک تۆمار بۆ هەر modelKey؛ mۆدێڵی نەناسراویش → x (خۆکار-نوێ)
            tier = "f" if b in NV_FREE_BOTS else ("p" if b in NV_PREM_CHEAP else "x")
            lbl = m.get("title") or k
            if lbl.startswith("models."):
                lbl = (NV_FREE_BOTS.get(b) or NV_PREMIUM_BOTS.get(b) or k)
            ok[k] = {"botId": b, "label": lbl, "tier": tier}
        if ok:
            MS["nv_ok"] = ok
            _ms_save()
            print(f"[NV-SYNC] کاتالۆگ {len(items)} → تۆمارکراو {len(ok)}", flush=True)
    except Exception as e:
        print(f"[NV-SYNC] {str(e)[:80]}", flush=True)


# ══════════ AllChatBots (allchatbots.ai) — §2.33 — Supabase + کوکی سێشن ══════════
# تێبینی: سایتەکە پارەدارە — بێ سەبسکریپشن 402 دەدات → tier=x (فەیلئۆڤەری خۆکار بۆ هەمان مۆدێڵ لە سەرچاوەکانی تر)
# ئەگەر ئەکاونتەکە سەبسکریپشی هەبوو → tier بگۆڕە بۆ f و هەموو ٤٨ مۆدێڵ ڕاستەوخۆ کار دەکەن
AL_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZlbHpxd2R4Zml0YXprcmt0eWtlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcxNTQ0OTMsImV4cCI6MjA5MjczMDQ5M30.3xKzSovrFhxu-ptma0-u_5QweO0QHjeBqWoLTbRasY0"
AL_SB = "https://felzqwdxfitazkrktyke.supabase.co"
AL_BASE = "https://allchatbots.ai"
AL_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
AL_COOKIE = "sb-felzqwdxfitazkrktyke-auth-token"
AL_ACC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "al_accounts.json")
AL_ST = {"sess": None, "sess_t": 0.0, "idx": 0,
         "accounts": [{"email": "pimeyax560@dreameg.com", "password": "pimeyax560@dreameg.com"}]}
_AL_SYNC = {"t": 0.0}
AL_MODELS = {
    "gpt-6-astra": "GPT-6 Astra", "gpt-5.6-sol": "GPT-5.6 Sol", "gpt-5.6-terra": "GPT-5.6 Terra",
    "gpt-5.6-luna": "GPT-5.6 Luna", "gpt-5.5": "GPT-5.5", "gpt-5.4": "GPT-5.4",
    "gpt-5.4-mini": "GPT-5.4 mini", "gpt-5.4-nano": "GPT-5.4 nano", "gpt-5": "GPT-5",
    "gpt-5-mini": "GPT-5 mini", "gpt-5-nano": "GPT-5 nano", "gpt-4.1": "GPT-4.1",
    "claude-opus-5": "Claude Opus 5", "claude-opus-4-8": "Claude Opus 4.8", "claude-opus-4-7": "Claude Opus 4.7",
    "claude-opus-4-6": "Claude Opus 4.6", "claude-opus-4-5": "Claude Opus 4.5", "claude-sonnet-5": "Claude Sonnet 5",
    "claude-sonnet-4-6": "Claude Sonnet 4.6", "claude-sonnet-4-5": "Claude Sonnet 4.5",
    "claude-haiku-4-5": "Claude Haiku 4.5", "claude-fable-5-1": "Claude Fable 5.1", "claude-fable-5": "Claude Fable",
    "gemini-3.1-pro": "Gemini 3.1 Pro", "gemini-2.5-pro": "Gemini 2.5 Pro", "gemini-3.8-flash": "Gemini 3.8 Flash",
    "gemini-3.7-flash": "Gemini 3.7 Flash", "gemini-3.6-flash": "Gemini 3.6 Flash", "gemini-3.5-flash": "Gemini 3.5 Flash",
    "gemini-2.5-flash": "Gemini 2.5 Flash", "gemini-3.1-flash-lite": "Gemini 3.1 Flash Lite",
    "grok-4.6": "Grok 4.6", "grok-4.5": "Grok 4.5", "grok-4": "Grok 4", "grok-3": "Grok 3", "grok-3-mini": "Grok 3 mini",
    "deepseek-v4-pro": "DeepSeek V4 Pro", "deepseek-v4-flash": "DeepSeek V4 Flash",
    "deepseek-chat": "DeepSeek V3", "deepseek-reasoner": "DeepSeek R1",
    "openrouter-auto": "OpenRouter Auto", "kimi-k3": "Kimi K3", "moonshot-32k": "Moonshot v1 32k",
    "moonshot-128k": "Moonshot v1 128k", "mistral-large": "Mistral Large", "mistral-medium": "Mistral Medium",
    "mistral-small": "Mistral Small", "auto": "Auto"}


def _al_load_acc():
    import json as _j
    try:
        d = _j.load(open(AL_ACC_FILE, encoding="utf-8"))
        if d.get("accounts"):
            AL_ST["accounts"] = d["accounts"]
        AL_ST["idx"] = int(d.get("idx") or 0)
    except Exception:
        pass


def _al_save_acc():
    import json as _j
    try:
        _j.dump({"accounts": AL_ST.get("accounts") or [], "idx": AL_ST["idx"]},
                open(AL_ACC_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


_al_load_acc()


def _al_login(force=False):
    """چوونەژوورەوەی Supabase — سێشن (~٥٠ خولەک کاش)"""
    import time as _t
    if not force and AL_ST.get("sess") and _t.time() - AL_ST.get("sess_t", 0) < 2700:
        return AL_ST["sess"]
    accs = AL_ST.get("accounts") or []
    if not accs:
        raise EMError("al: هیچ ئەکاونت")
    acc = accs[AL_ST["idx"] % len(accs)]
    try:
        r = requests.post(AL_SB + "/auth/v1/token?grant_type=password",
                          headers={"apikey": AL_KEY, "Content-Type": "application/json"},
                          json={"email": acc["email"], "password": acc["password"]}, timeout=(10, 25))
    except Exception as e:
        raise EMError(f"al: {str(e)[:60]}")
    if r.status_code != 200 or not (r.json() or {}).get("access_token"):
        raise EMError("al: چوونەژوورەوە شکست")
    AL_ST["sess"] = r.json()
    AL_ST["sess_t"] = _t.time()
    _al_save_acc()
    return AL_ST["sess"]


def al_chat(messages, model_id, timeout=110):
    """چاتی AllChatBots — کوکی سێشن + /api/chat — 402 → فەیلئۆڤەر"""
    sess = _al_login()
    lines = []
    for m in messages[-12:]:
        role = m.get("role")
        c = (m.get("content") or "").strip()
        if not c:
            continue
        if role == "system":
            lines.append("[Instructions] " + c)
        elif role == "user":
            lines.append("[User] " + c)
        else:
            lines.append("[Assistant] " + c)
    if not lines:
        raise EMError("al: هیچ نامە")
    lines.append("[Assistant]")
    prompt = "\n".join(lines)[-6000:]
    H = {"User-Agent": AL_UA, "Content-Type": "application/json",
         "Origin": "https://allchatbots.ai", "Referer": "https://allchatbots.ai/"}
    ck = {AL_COOKIE: json.dumps(sess)}
    body = {"messages": [{"role": "user", "content": prompt}], "modelId": model_id, "stream": False}
    for attempt in range(2):
        try:
            r = requests.post(AL_BASE + "/api/chat", json=body, headers=H, cookies=ck, timeout=(15, timeout))
        except Exception as e:
            raise EMError(f"al: {str(e)[:60]}")
        if r.status_code in (401, 403) and attempt == 0:
            sess = _al_login(force=True)
            ck = {AL_COOKIE: json.dumps(sess)}
            continue
        if r.status_code == 402:
            raise EMError("al: پرێمیۆمی-قورس — بە پارە بەردەستە")  # → فەیلئۆڤەری هەمان مۆدێڵ
        if r.status_code == 429:
            raise EMError("al: لیمیت")
        if r.status_code != 200:
            raise EMError(f"al: HTTP{r.status_code}")
        ct = (r.headers.get("content-type") or "")
        if "text/event" in ct:
            parts = []
            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                try:
                    d = json.loads(line[5:].strip())
                except Exception:
                    continue
                for k in ("content", "text", "delta"):
                    v = d.get(k)
                    if isinstance(v, str):
                        parts.append(v)
                        break
            ans = "".join(parts).strip()
        else:
            try:
                j = r.json()
            except Exception:
                raise EMError("al: وەڵامی نەناسراو")
            ans = ""
            for cand in (j.get("content"), j.get("message"), j.get("text"),
                         (j.get("choices") or [{}])[0].get("message", {}).get("content") if isinstance(j.get("choices"), list) else None):
                if isinstance(cand, str) and cand.strip():
                    ans = cand.strip()
                    break
        if ans:
            return ans
        raise EMError("al: بەتاڵ")
    raise EMError("al: شکست")


def al_servers():
    out = []
    for k, lbl in sorted(AL_MODELS.items()):
        slug = re.sub(r"[^a-z0-9]+", "-", str(k).lower()).strip("-") or "model"
        out.append({"id": f"al-{slug}", "name": f"{lbl} (AL)", "model_id": k, "kind": "al"})
    return out


def sync_al_models(force=False):
    """تۆمارکردنی کاتالۆگی AL — ٦ کاتژمێر (لیستی ناو-کۆد — لە چانکەکانی فرۆنتئێند دەرهێنراوە)"""
    import time as _t
    if not force and _t.time() - _AL_SYNC["t"] < 21600:
        return
    _AL_SYNC["t"] = _t.time()
    ok = {k: {"label": lbl, "tier": "x"} for k, lbl in AL_MODELS.items()}
    if ok:
        MS["al_ok"] = ok
        _ms_save()
        print(f"[AL-SYNC] تۆمارکراو {len(ok)}", flush=True)


# ══════════ AI/ML API (aimlapi.com) — §2.34 — دەروازەی 938 مۆدێڵ (پارەدار — tier-x) ══════════
# لۆگین: PUT auth.aimlapi.com/v1/auth/account {email,password} + aim-device-id → token (~11کاتژمێر)
# کلیل: POST app.aimlapi.com/v1/keys → چات: POST api.aimlapi.com/v1/chat/completions (OpenAI-جۆر)
# ئەکاونت بێ-فەندز → 403 → هەڵەی جوان → فەیلئۆڤەری هەمان مۆدێڵ لە سەرچاوەکانی تر
AIML_ACC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aiml_key.json")
AIML_ST = {"tok": None, "tok_t": 0.0, "key": None,
           "email": "pimeyax560@dreameg.com", "password": "12345678Rkjk@&"}
_AIML_SYNC = {"t": 0.0}
AIML_MODELS = {
    "openai/gpt-6-astra": "GPT-6 Astra", "openai/gpt-5.6-sol-pro": "GPT-5.6 Sol Pro",
    "openai/gpt-5.6-sol": "GPT-5.6 Sol", "openai/gpt-5.6-terra-pro": "GPT-5.6 Terra Pro",
    "openai/gpt-5.6-terra": "GPT-5.6 Terra", "openai/gpt-5.6-luna-pro": "GPT-5.6 Luna Pro",
    "openai/gpt-5.6-luna": "GPT-5.6 Luna", "openai/gpt-5-5-pro": "GPT-5.5 Pro",
    "openai/gpt-5-5": "GPT-5.5", "openai/gpt-5-4-pro": "GPT-5.4 Pro", "openai/gpt-5-4": "GPT-5.4",
    "openai/gpt-5.4-mini": "GPT-5.4 Mini", "openai/gpt-5.4-nano": "GPT-5.4 Nano",
    "openai/gpt-5-3-codex": "GPT-5.3 Codex", "openai/gpt-5-2-pro": "GPT-5.2 Pro",
    "openai/gpt-5-2": "GPT-5.2", "openai/gpt-5-1": "GPT-5.1", "openai/gpt-5": "GPT-5",
    "openai/gpt-5-mini": "GPT-5 Mini", "openai/gpt-5-nano": "GPT-5 Nano",
    "openai/gpt-4.1": "GPT-4.1", "openai/gpt-4o": "GPT-4o", "openai/gpt-4o-mini": "GPT-4o Mini",
    "openai/o3-pro": "o3 Pro", "openai/o3-mini": "o3 Mini", "openai/gpt-oss-120b": "GPT OSS 120B",
    "anthropic/claude-opus-5": "Claude Opus 5", "anthropic/claude-opus-4.8": "Claude Opus 4.8",
    "anthropic/claude-opus-4.7": "Claude Opus 4.7", "anthropic/claude-opus-4.5": "Claude Opus 4.5",
    "anthropic/claude-sonnet-5": "Claude Sonnet 5", "anthropic/claude-sonnet-4.6": "Claude Sonnet 4.6",
    "anthropic/claude-haiku-4.5": "Claude 4.5 Haiku", "anthropic/claude-fable-5.1": "Claude Fable 5.1",
    "anthropic/claude-fable-5": "Claude Fable 5", "anthropic/claude-3-haiku": "Claude 3 Haiku",
    "google/gemini-3.8-flash": "Gemini 3.8 Flash", "google/gemini-3.7-flash": "Gemini 3.7 Flash",
    "google/gemini-3.6-flash": "Gemini 3.6 Flash", "google/gemini-3.5-flash": "Gemini 3.5 Flash",
    "google/gemini-3.1-pro-preview": "Gemini 3.1 Pro", "google/gemini-3.1-flash-lite": "Gemini 3.1 Flash Lite",
    "google/gemini-2.5-pro": "Gemini 2.5 Pro", "google/gemini-2.5-flash": "Gemini 2.5 Flash",
    "google/gemma-4-31b-it": "Gemma 4 31B",
    "x-ai/grok-4-6": "Grok 4.6", "x-ai/grok-4-5": "Grok 4.5", "x-ai/grok-4-3": "Grok 4.3",
    "x-ai/grok-4-20-0309-reasoning": "Grok 4.20", "x-ai/grok-4-1-fast-reasoning": "Grok 4.1 Fast",
    "x-ai/grok-code-fast-1": "Grok Code Fast",
    "moonshot/kimi-k3": "Kimi K3", "moonshot/kimi-k2-7-code": "Kimi K2.7 Code",
    "moonshot/kimi-k2-5": "Kimi K2.5", "moonshotai/kimi-latest": "Kimi Latest",
    "deepseek/deepseek-v4.1-flash": "DeepSeek V4.1 Flash", "deepseek/deepseek-v4-pro": "DeepSeek V4 Pro",
    "deepseek/deepseek-v4-flash": "DeepSeek V4 Flash", "deepseek/deepseek-chat": "DeepSeek Chat",
    "deepseek/deepseek-reasoner": "DeepSeek R1", "deepseek/deepseek-thinking-v3.2-exp": "DeepSeek V3.2 Think",
    "minimax/minimax-m3": "MiniMax M3", "minimax/m2-7-highspeed": "MiniMax M2.7",
    "minimax/m2-5-20260218": "MiniMax M2.5", "minimax/m1": "MiniMax M1",
    "zhipu/glm-5.3": "GLM 5.3", "zhipu/glm-5.2": "GLM 5.2", "zhipu/glm-5-1": "GLM 5.1",
    "zhipu/glm-5": "GLM 5", "zhipu/glm-4.7": "GLM 4.7", "z-ai/glm-5v-turbo": "GLM 5V Turbo",
    "alibaba/qwen3.8-max": "Qwen 3.8 Max", "alibaba/qwen3.8-flash": "Qwen 3.8 Flash",
    "alibaba/qwen3.7-max": "Qwen 3.7 Max", "alibaba/qwen3.6-plus": "Qwen 3.6 Plus",
    "alibaba/qwen3-max": "Qwen 3 Max",
    "bytedance/seed-2-0-pro": "Seed 2.0 Pro", "bytedance/seed-2-0-lite": "Seed 2.0 Lite",
    "bytedance/seed-2-0-mini": "Seed 2.0 Mini", "bytedance/seed-1-8": "Seed 1.8",
    "meta/muse-spark-1.3": "Muse Spark 1.3", "meta/muse-glimmer-30b": "Muse Glimmer 30B",
    "nvidia/nemotron-3-ultra-550b-a55b": "Nemotron 3 Ultra", "nvidia/nemotron-3-super-120b-a12b": "Nemotron 3 Super",
    "nvidia/nemotron-3-nano-30b-a3b": "Nemotron 3 Nano",
    "tencent/hy4-preview": "Hy4 Preview", "tencent/hy3": "Hy3",
    "baidu/ernie-5.0": "ERNIE 5.0", "amazon/nova-pro-v1": "Nova Pro 1.0",
    "amazon/nova-lite-v1": "Nova Lite 1.0", "amazon/nova-micro-v1": "Nova Micro 1.0",
    "stepfun/step-3.7-flash": "Step 3.7 Flash", "xiaomi/mimo-v2.5-pro": "MiMo V2.5 Pro",
    "upstage/solar-pro4": "Solar Pro 4", "writer/palmyra-x5": "Palmyra X5",
    "thinkingmachines/inkling": "Inkling", "inception/mercury-2.5": "Mercury 2.5",
    "mistralai/mistral-medium-3.5": "Mistral Medium 3.5", "mistralai/mistral-large": "Mistral Large",
    "mistralai/codestral-2508": "Codestral", "cohere/command-a": "Command A",
    "perplexity/sonar-pro": "Sonar Pro", "perplexity/sonar": "Sonar",
    "nousresearch/hermes-4-405b": "Hermes 4 405B", "ibm-granite/granite-4.2-8b": "Granite 4.2 8B",
    "sakana/fugu-ultra-v2": "Fugu Ultra v2", "stealth/union-alpha": "Union Alpha",
    "typesafe/jev": "Jev 1.13", "meituan/longcat-2.0": "LongCat 2.0", "poolside/laguna-s-2.1": "Laguna S 2.1"}


def _aiml_load():
    import json as _j
    try:
        d = _j.load(open(AIML_ACC_FILE, encoding="utf-8"))
        AIML_ST["key"] = d.get("key")
    except Exception:
        pass


def _aiml_save():
    import json as _j
    try:
        _j.dump({"key": AIML_ST.get("key")}, open(AIML_ACC_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


_aiml_load()


def _aiml_login():
    import time as _t, uuid as _u
    if AIML_ST.get("tok") and _t.time() - AIML_ST.get("tok_t", 0) < 30000:
        return AIML_ST["tok"]
    try:
        r = requests.put("https://auth.aimlapi.com/v1/auth/account",
                         json={"email": AIML_ST["email"], "password": AIML_ST["password"]},
                         headers={"aim-device-id": str(_u.uuid4()), "User-Agent": "Mozilla/5.0",
                                  "Origin": "https://aimlapi.com", "Referer": "https://aimlapi.com/"},
                         timeout=(15, 30))
        if r.status_code != 200:
            raise EMError(f"aiml-login {r.status_code}")
        AIML_ST["tok"] = r.json().get("token")
        AIML_ST["tok_t"] = _t.time()
        return AIML_ST["tok"]
    except EMError:
        raise
    except Exception as e:
        raise EMError(f"aiml: {str(e)[:60]}")


def _aiml_ensure_key():
    tok = _aiml_login()
    H = {"Authorization": f"Bearer {tok}", "User-Agent": "Mozilla/5.0"}
    if AIML_ST.get("key"):
        return AIML_ST["key"]
    # کیلی هەیە؟
    r = requests.get("https://app.aimlapi.com/v1/keys", headers=H, timeout=(15, 30))
    items = (r.json() or {}).get("items") or []
    if not items:
        r2 = requests.post("https://app.aimlapi.com/v1/keys", headers=H, json={"name": "ta3afi"}, timeout=(15, 30))
        if r2.status_code not in (200, 201):
            raise EMError(f"aiml-key {r2.status_code}")
        items = [r2.json()]
    # تەنها لە کاتی دروستکردندا key تەواو دەدرێت — ئەگەر کۆنەکە نەمانەوە، دووبارە دروست بکە
    full = (items[0] or {}).get("key")
    if not full:
        r3 = requests.post("https://app.aimlapi.com/v1/keys", headers=H, json={"name": "ta3afi"}, timeout=(15, 30))
        if r3.status_code not in (200, 201):
            raise EMError(f"aiml-key {r3.status_code}")
        full = (r3.json() or {}).get("key")
    if not full:
        raise EMError("aiml: هیچ کلیل")
    AIML_ST["key"] = full
    _aiml_save()
    return full


def aiml_chat(messages, model_id, timeout=110):
    """چاتی AI/ML API — OpenAI-جۆر — 403 (فەندز) → فەیلئۆڤەر"""
    lines = []
    for m in messages[-12:]:
        role = m.get("role")
        c = (m.get("content") or "").strip()
        if not c:
            continue
        lines.append({"role": role, "content": c})
    if not lines:
        raise EMError("aiml: هیچ نامە")
    key = _aiml_ensure_key()
    try:
        r = requests.post("https://api.aimlapi.com/v1/chat/completions",
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                   "User-Agent": "Mozilla/5.0"},
                          json={"model": model_id, "messages": lines}, timeout=(15, timeout))
    except Exception as e:
        raise EMError(f"aiml: {str(e)[:60]}")
    if r.status_code in (401, 403):
        try:
            j = r.json()
        except Exception:
            j = {}
        msg = str((j.get("message") or j.get("error") or ""))[:60]
        if "funds" in msg.lower():
            raise EMError("aiml: پارەدار — بە فەندز بەردەستە")  # → فەیلئۆڤەر
        if r.status_code == 401:
            AIML_ST["tok"] = None
            raise EMError("aiml: توکن")
        raise EMError(f"aiml: {msg or r.status_code}")
    if r.status_code == 429:
        raise EMError("aiml: لیمیت")
    if r.status_code != 200:
        raise EMError(f"aiml: HTTP{r.status_code}")
    try:
        j = r.json()
        ans = (j.get("choices") or [{}])[0].get("message", {}).get("content", "")
        if isinstance(ans, list):
            ans = "".join(x.get("text", "") for x in ans if isinstance(x, dict))
        ans = (ans or "").strip()
        if ans:
            return ans
    except Exception:
        pass
    raise EMError("aiml: بەتاڵ")


def aiml_servers():
    out = []
    for k, lbl in sorted(AIML_MODELS.items()):
        slug = re.sub(r"[^a-z0-9]+", "-", str(k).lower()).strip("-") or "model"
        out.append({"id": f"aiml-{slug}", "name": f"{lbl} (AI/ML)", "model_id": k, "kind": "aiml"})
    return out


def sync_aiml_models(force=False):
    """تۆمارکردنی کاتالۆگی AI/ML — ٦ کاتژمێر — tier=x"""
    import time as _t
    if not force and _t.time() - _AIML_SYNC["t"] < 21600:
        return
    _AIML_SYNC["t"] = _t.time()
    ok = {k: {"label": lbl, "tier": "x"} for k, lbl in AIML_MODELS.items()}
    if ok:
        MS["aiml_ok"] = ok
        _ms_save()
        print(f"[AIML-SYNC] تۆمارکراو {len(ok)}", flush=True)


def _ms_dup(servers, model_id):
    """ئایا ئەم مۆدێڵە پێشتر لە سەرچاوەیەکی تر هەیە؟ — دژە-دووبارە"""
    n = norm_model(model_id)
    if not n:
        return True
    for x in servers:
        if n in norm_model(x["id"]) or n in norm_model(str(x.get("model_id", ""))):
            return True
    return False


def sync_duck_models(servers):
    """لیستی مۆدێڵە ڕاییگەکانی duck.ai ڕاستەوخۆ لە bundle ی فەرمی — هەر ٣٠ خولەک"""
    if time.time() - MS_T["duck"] < 1800:
        return
    with MS_LOCK:
        if time.time() - MS_T["duck"] < 1800:
            return
        MS_T["duck"] = time.time()
    try:
        s = _duck_session()
        r = s.get("https://duck.ai/", headers={"Accept": "text/html", "Upgrade-Insecure-Requests": "1"},
                  timeout=(15, 25))
        m = re.search(r'(/dist/duckai-dist/entry\.duckai\.[A-Za-z0-9]+\.js)', r.text)
        if not m:
            print("[SYNC] duck: bundle نەدۆزرایەوە", flush=True)
            return
        r2 = s.get("https://duck.ai" + m.group(1), timeout=(15, 40))
        js = r2.text
        found = {}
        for mo in re.finditer(r'\{model:"([a-z0-9./\-]+)",modelName:"[^"]*",modelVariant:"([^"]*)",'
                              r'modelShortName:"([^"]*)".{0,600}?availableTo:\[([^\]]*)\]', js):
            mid, variant, short, avail = mo.group(1), mo.group(2), mo.group(3), mo.group(4)
            if "Free" not in avail:
                continue
            found[mid] = short or variant or mid
        for mo in re.finditer(r'\{model:"([a-z0-9./\-]+)",upgradeModel:"[^"]+"\}', js):
            found.pop(mo.group(1), None)  # مردووەکان لاببە
        newd = {}
        for mid, short in found.items():
            slug = re.sub(r'[^a-z0-9.]+', '-', mid.lower()).strip('-')
            newd[mid] = {"id": f"duck-{slug}", "name": f"{short} (Duck)",
                         "model_id": mid, "kind": "duck"}
        old_ids = set(MS.get("duck", {}).keys())
        MS["duck"] = newd
        _ms_save()
        extras = [k for k in newd if not _ms_dup(servers, k)]
        print(f"[SYNC] duck: {len(newd)} مۆدێڵی ڕاییگە ({','.join(newd)}) | نوێ: {extras}", flush=True)
    except Exception as e:
        print(f"[SYNC] duck هەڵە: {str(e)[:80]}", flush=True)


def sync_ak_models(servers):
    """anakin — مۆدێڵی نوێی لیستی گشتی → پڕۆب ی بچووک؛ تەنها ئەوەی میوان کاری دەکات زیاد دەکرێت"""
    if time.time() - MS_T["ak"] < 3600:
        return
    with MS_LOCK:
        if time.time() - MS_T["ak"] < 3600:
            return
        MS_T["ak"] = time.time()
    try:
        r = requests.get("https://api.anakin.ai/api/v1/ai-models?locale=en-US",
                         headers={"User-Agent": DUCK_UA, "Origin": "https://app.anakin.ai",
                                  "Referer": "https://app.anakin.ai/", "x-client-mode": "web"},
                         timeout=(15, 25))
        data = r.json().get("data") or []
        cands = []
        for x in data:
            if not isinstance(x, dict):
                continue
            mid = x.get("modelId")
            types = x.get("types") or []
            label = str(x.get("label") or "")
            if not mid or int(mid) in (308, 309) or "chat" not in types:
                continue
            if x.get("comingSoon") or x.get("legacy"):
                continue
            if re.search(r'flex|thinking|high|low|minimal', label, re.I):
                continue
            if str(mid) in MS["ak_ok"] or str(mid) in MS["ak_block"]:
                continue
            cands.append((int(mid), label))
        cands.sort(reverse=True)  # نوێترین پێشتر
        if not cands:
            return
        # سەرەتا پشکنینی تەندروستی — ٣٠٩ دەبێت کار بکات، ئەگینا IP لە cooldown ە و پڕۆب ڕاست ناکات
        def _probe(mid, content="hi"):
            payload = json.dumps({"app_id": 19510, "model_id": int(mid),
                                  "messages": [{"role": "user", "content": content}]})
            p = subprocess.run([NODE_BIN, AK_CLIENT], input=payload.encode("utf-8"),
                               capture_output=True, timeout=60)
            lines = [l for l in (p.stdout or b"").decode("utf-8", "replace").strip().splitlines() if l.strip()]
            return json.loads(lines[-1]) if lines else {}
        chk = _probe(309)
        if not (chk.get("ok") and chk.get("answer")):
            print("[SYNC] ak: ٣٠٩ وەڵام نەدایەوە — IP لە cooldown ە، پڕۆب دوادەخرێت", flush=True)
            return
        mid, label = cands[0]
        res = _probe(mid, "Say exactly: OK")
        if res.get("ok") and res.get("answer"):
            MS["ak_ok"][str(mid)] = {"label": label, "t": time.time()}
            print(f"[SYNC] ak: مۆدێڵی نوێی میوان ✅ {mid} {label}", flush=True)
        else:
            MS["ak_block"][str(mid)] = {"label": label, "t": time.time()}
            print(f"[SYNC] ak: {mid} {label} بۆ میوان کراوە نییە", flush=True)
        _ms_save()
    except Exception as e:
        print(f"[SYNC] ak هەڵە: {str(e)[:80]}", flush=True)


def _apply_model_sync(servers):
    """هەموو مۆدێڵە دۆزراوەکان زیاد دەکرێن — بێ سڕینەوەی هیچ سەرچاوەیەک؛
       مینیو خۆی دووەکییەکان یەک دەخات (dedupe_servers) و بەک-ئێند هەردووکیان دەیهێڵێتەوە"""
    out = list(servers)
    for mid, e in MS.get("duck", {}).items():
        if not any(x["id"] == e["id"] for x in out):
            out.append(dict(e))
    for mid, info in MS.get("ak_ok", {}).items():
        sid = f"ak-{re.sub(r'[^a-z0-9]+', '-', str(info.get('label', mid)).lower()).strip('-') or mid}-{mid}"
        if not any(x["id"] == sid for x in out):
            out.append({"id": sid, "name": f"{info.get('label', mid)} (Anakin)",
                        "model_id": str(mid), "kind": "ak"})
    return out


# ─── یەکسانکردنی مۆدێڵ بۆ fallback — هەمان خێزان لە سەرچاوەیەکی تر ───
_MODEL_HINTS = [
    ("gemini", "gemini"), ("claude", "claude"), ("grok", "grok"),
    ("kimi", "kimi"), ("moonshot", "kimi"), ("qwen", "qwen"),
    ("glm", "glm"), ("z-ai", "glm"), ("deepseek", "deepseek"),
    ("llama", "llama"), ("meta-llama", "llama"), ("phi", "phi"),
    ("hy3", "hy3"), ("tencent", "hy3"), ("gemma", "gemma"),
    ("oss", "gpt"), ("o4", "gpt"), ("o3", "gpt"), ("gpt", "gpt"),
]


def _model_family(mid):
    s = str(mid).lower()
    for k, fam in _MODEL_HINTS:
        if k in s:
            return fam
    return "gpt"


def pick_in_kind(servers, kind, wanted):
    """باشترین مۆدێڵی هاوشێوە لە سەرچاوەیەکی تر — بۆ fallback ی ورد"""
    fam = _model_family(wanted)
    same = [x for x in servers if x.get("kind") == kind]
    if not same:
        return None
    for x in same:
        if _model_family(x["id"]) == fam:
            return x
    return same[0]


# ════════════════════════════════════════════════════════════
# ٣) کلایەنتی aifreeforever
# ════════════════════════════════════════════════════════════

class AIFreeError(Exception):
    pass


class AIFreeChat:
    def __init__(self, model, endpoint=None, timeout=120):
        self.model = model
        self.endpoint = endpoint if (endpoint or "").startswith("http") else BASE_URL + (endpoint or "")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": UA,
            "Content-Type": "application/json",
            "Origin": BASE_URL,
            "Referer": BASE_URL + "/chat/" + model,
        })
        self._nonce = ""

    def _fetch_nonce(self):
        n = ""
        try:
            n = self.session.get(BASE_URL + "/api/chat-nonce", timeout=15).json().get("nonce", "")
        except Exception:
            n = ""
        if not n:
            # ماڵپەرەکە نۆنس بەتاڵ دەدات مەگەر سەرەتا سەردانی پەڕەی چات بکرێت (کوکی سێشن)
            try:
                self.session.headers.pop("Content-Type", None)
                self.session.get(BASE_URL + "/chat/" + self.model, timeout=20)
                self.session.headers["Content-Type"] = "application/json"
                n = self.session.get(BASE_URL + "/api/chat-nonce", timeout=15).json().get("nonce", "")
            except Exception:
                n = ""
        return n

    @staticmethod
    def _proof():
        now = int(time.time() * 1000)
        start = now - random.randint(4000, 15000)
        return {"nonce": "", "keystrokeCount": random.randint(20, 120),
                "pasteEvents": 0, "totalTypingTime": now - start,
                "startTime": start, "submitTime": now}

    def chat(self, question, history=None):
        payload = {
            "model": self.model, "question": question, "tone": "friendly",
            "format": "paragraph", "file": None,
            "conversationHistory": (history or [])[-20:],
            "interactionProof": self._proof(),
            "aiRole": "assistant", "aiName": "", "language": "auto",
        }
        last = None
        for attempt in range(3):
            try:
                if not self._nonce:
                    self._nonce = self._fetch_nonce()
                payload["interactionProof"]["nonce"] = self._nonce
                with self.session.post(self.endpoint, json=payload, stream=True,
                                       timeout=(15, self.timeout)) as r:
                    if r.status_code == 429:
                        raise AIFreeError("طلبات كثيرة بسرعة (429) — انتظر قليلا.")
                    if r.status_code in (403, 407, 502, 503):
                        raise ConnectionError(f"داخستن ({r.status_code})")
                    if r.status_code == 409:
                        raise AIFreeError("سێرڤەرەکە ئێستا بەردەست نییە (409).")
                    r.raise_for_status()
                    ctype = r.headers.get("content-type", "")
                    answer = ""
                    if "text/event-stream" in ctype:
                        for raw in r.iter_lines():
                            line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
                            if not line.startswith("data: "):
                                continue
                            d = line[6:].strip()
                            if d == "[DONE]":
                                break
                            try:
                                answer += json.loads(d).get("token", "")
                            except Exception:
                                pass
                    else:
                        answer = (r.json() or {}).get("answer", "")
                    if not answer:
                        raise ConnectionError("aff: وەڵامی بەتاڵ — نۆنسی نوێ پێویستە")
                    return answer
            except AIFreeError:
                raise
            except Exception as e:
                last = e
                self._nonce = ""
                time.sleep(1.2 * (attempt + 1))
        raise ConnectionError(str(last))


# ════════════════════════════════════════════════════════════
# ٤) API — ڕووکاری HTTP (OpenAI-compatible + سادە)
# ════════════════════════════════════════════════════════════

API_PORT = int(os.environ.get("API_PORT", 8080))
API_KEY = os.environ.get("API_KEY", "")  # ئەگەر دانرابێت — پێویستە لە هەر داواکارییەک

# ─── پرۆمپتی بنەڕەتی API — شێوازی پرسیار و وەڵامی شەرعی (کوردی) ───
# ئەگەر ئەپەکەت سیستەم پرۆمپتی خۆی نەنێرێت، ئەمە بەکاردێت
# ⚡ مێشکی سەربەخۆی API — تەواو جیاواز لە بۆتی تێلەگرام
# بێ سیستەم پرۆمپت، بێ کەسایەتی، بێ یاساکانی بۆتەکە
API_BRAIN = {"mode": None, "servers": [], "t": 0.0}
API_REFRESH_SEC = 300


def detect_brain_api():
    """هەمان لیستی بۆت — easemate + aifreeforever + pollinations"""
    return detect_brain(allow_fallback=True)


def api_brain_ensure():
    """لیستی سێرڤەرەکانی API تازە دەکاتەوە — هەر ٥ خولەک، سەربەخۆ"""
    if API_BRAIN["servers"] and time.time() - API_BRAIN["t"] < API_REFRESH_SEC:
        return
    new = detect_brain_api()
    if new["servers"]:
        API_BRAIN["mode"], API_BRAIN["servers"] = new["mode"], new["servers"]
        rebuild_aliases(new["servers"])
        API_BRAIN["t"] = time.time()
        print(f"[API-BRAIN] {new['mode']} ({len(new['servers'])} سێرڤەر)", flush=True)


def _api_servers():
    # ناوە ڕاستەقینەکانی مۆدەڵەکان — یەک دەنگ بۆ هەر مۆدێڵ (دووەکی سەرچاوەکان لە بەک-ئێند دەمێننەوە)
    return [{"alias": x["id"], "id": x["id"], "name": x.get("name", x["id"])}
            for x in dedupe_servers(API_BRAIN["servers"])]


def _resolve_server(ref):
    ref = str(ref).strip().lower()
    for i, x in enumerate(API_BRAIN["servers"], 1):
        if ref in (f"server-{i}", str(i)) or ref == str(x["id"]).lower() or ref == str(x.get("alias", "")).lower():
            y = dict(x)
            y["alias"] = f"server-{i}"
            return y
    num = ref[3:] if ref.startswith("em-") else ref
    if num.isdigit():
        for x in API_BRAIN["servers"]:
            if x.get("kind") == "em" and str(x["model_id"]) == num:
                y = dict(x)
                y["alias"] = x["id"]
                return y
    return None


class APIHandler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, X-API-Key, Content-Type")
        self.end_headers()

    def log_message(self, *a):
        pass

    def _authed(self):
        if not API_KEY:
            return True
        h = self.headers.get("Authorization", "")
        k = self.headers.get("X-API-Key", "")
        return h == f"Bearer {API_KEY}" or k == API_KEY

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        if self.path in ("/", "/health"):
            api_brain_ensure()
            self._send(200, {"ok": True, "service": "smart-chatbot-api",
                             "mode": API_BRAIN["mode"], "servers": len(API_BRAIN["servers"])})
        elif self.path in ("/models", "/v1/models"):
            if not self._authed():
                return self._send(401, {"error": "API_KEY هەڵەیە — Authorization: Bearer <key>"})
            api_brain_ensure()
            data = [{"id": s["alias"], "object": "model", "owned_by": "smart-chatbot"}
                    for s in _api_servers()]
            self._send(200, {"object": "list", "data": data})
        else:
            self._send(404, {"error": "not found — /v1/chat/completions و /v1/models"})

    def do_POST(self):
        if self.path not in ("/chat", "/v1/chat/completions"):
            return self._send(404, {"error": "not found"})
        if not self._authed():
            return self._send(401, {"error": "API_KEY هەڵەیە — Authorization: Bearer <key>"})

        try:
            body = self._body()
        except Exception:
            return self._send(400, {"error": "bad json"})

        openai_style = self.path == "/v1/chat/completions"
        want_stream = bool(body.get("stream")) and openai_style

        if openai_style:
            ref = body.get("model") or "1"
            msgs = body.get("messages") or []
            q = ""
            for m in reversed(msgs):
                if m.get("role") == "user":
                    q = m.get("content", "")
                    break
            history = [{"role": m.get("role", "user"), "content": m.get("content", "")}
                       for m in msgs if m.get("role") in ("user", "assistant", "system")][-20:]
        else:
            ref = body.get("server") or body.get("model") or 1
            q = (body.get("message") or "").strip()
            history = body.get("history") or []
            msgs = history + [{"role": "user", "content": q}]

        if not q:
            return self._send(400, {"error": "پرسیار بەتاڵە"})


        api_brain_ensure()
        if not _resolve_server(ref):
            return self._send(400, {"error": f"خادم غير معروف: {ref} — راجع /v1/models"})
        srv = _resolve_server(ref)

        print(f"[API] server={srv['id']} q={q[:50]}", flush=True)

        # ⚡ API سەربەخۆیە: تەنها نامەکانی داواکار بەکاردەهێنێت —
        # هیچ سیستەم پرۆمپت یان یاسای بۆتەکە لێرەدا نییە
        # زنجیرەی هەوڵ: سێرڤەری هەڵبژێردراو + یەکێک لە هەر سەرچاوەیەکی تر
        order = [srv]
        # ⚡ فەڵباکی خێرا: هەمان مۆدێڵ لە سەرچاوەی تر
        for alt in MODEL_SOURCES.get(srv_key(srv), []):
            if alt["id"] != srv["id"] and alt not in order:
                order.append(alt)
        for kind in ("em", "aff", "cbc", "rwd", "l7", "g4f", "pol"):
            if srv.get("kind") != kind:
                cand = pick_in_kind(API_BRAIN["servers"], kind, srv["id"])
                if cand and cand not in order:
                    order.append(cand)

        content, last_err = "", None
        for cand in order:
            try:
                kind = cand.get("kind")
                if kind == "em":
                    content = em_chat(history, cand["model_id"])
                elif kind == "aff":
                    content = AIFreeChat(model=cand["id"], endpoint=cand.get("endpoint")).chat(q, history=history)
                elif kind == "cbc":
                    content = cbc_chat(history)
                elif kind == "rwd":
                    content = rwd_chat(cand["model_id"], history + [{"role": "user", "content": q}])
                elif kind == "act":
                    content = act_chat(cand["model_id"], history + [{"role": "user", "content": q}])
                elif kind == "fla":
                    content = fla_chat(history + [{"role": "user", "content": q}])
                elif kind == "z02":
                    content = z02_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "qb":
                    content = qb_chat(history + [{"role": "user", "content": q}])
                elif kind == "duck":
                    content = duck_chat(cand["model_id"], history + [{"role": "user", "content": q}])
                elif kind == "ak":
                    content = ak_chat(cand["model_id"], history + [{"role": "user", "content": q}])
                elif kind == "ng":
                    content = ng_chat(history + [{"role": "user", "content": q}])
                elif kind == "l7":
                    content = l7_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "g4f":
                    content = g4f_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "ct":
                    content = ct_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "yl":
                    content = yl_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "hk":
                    content = hk_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "hf":
                    content = hf_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "aka":
                    content = aka_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "hb":
                    content = hb_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "gk":
                    content = gk_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "gz":
                    content = gz_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "pi":
                    content = pi_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "cb":
                    content = cb_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "ca":
                    content = ca_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "ac":
                    content = ac_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "nv":
                    content = nv_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "al":
                    content = al_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                elif kind == "aiml":
                    content = aiml_chat(history + [{"role": "user", "content": q}], cand["model_id"])
                else:
                    content = pol_chat(cand["id"], history + [{"role": "user", "content": q}])
                if content:
                    if cand is not srv:
                        print(f"[API] fallback → {kind}", flush=True)
                    break
            except Exception as e:
                last_err = e
                print(f"[API] {cand.get('kind')} هەڵە: {str(e)[:90]}", flush=True)
        if not content:
            # ═══ دیلی نەوە (API): مۆدێڵی داواکراو مردووە → نوێترین نەوەی هەمان خێزان ═══
            try:
                up = smart_rebind(API_BRAIN["servers"], srv["id"])
                if up and up != srv["id"]:
                    nsrv = next(x for x in API_BRAIN["servers"] if x["id"] == up)
                    print(f"[API] 🔄 دیلی نەوە: {srv['id']} → {up}", flush=True)
                    k = nsrv.get("kind")
                    nmsgs = history + [{"role": "user", "content": q}]
                    if k == "em":
                        content = em_chat(nmsgs, nsrv["model_id"])
                    elif k == "cbc":
                        content = cbc_chat(nmsgs)
                    elif k == "rwd":
                        content = rwd_chat(nsrv["model_id"], nmsgs)
                    elif k == "act":
                        content = act_chat(nsrv["model_id"], nmsgs)
                    elif k == "fla":
                        content = fla_chat(nmsgs)
                    elif k == "z02":
                        content = z02_chat(nmsgs, nsrv["model_id"])
                    elif k == "qb":
                        content = qb_chat(nmsgs)
                    elif k == "duck":
                        content = duck_chat(nsrv["model_id"], nmsgs)
                    elif k == "ak":
                        content = ak_chat(nsrv["model_id"], nmsgs)
                    elif k == "ng":
                        content = ng_chat(nmsgs)
                    elif k == "l7":
                        content = l7_chat(nmsgs, nsrv["model_id"])
                    elif k == "g4f":
                        content = g4f_chat(nmsgs, nsrv["model_id"])
                    elif k == "ct":
                        content = ct_chat(nmsgs, nsrv["model_id"])
                    elif k == "yl":
                        content = yl_chat(nmsgs, nsrv["model_id"])
                    elif k == "hk":
                        content = hk_chat(nmsgs, nsrv["model_id"])
                    elif k == "hf":
                        content = hf_chat(nmsgs, nsrv["model_id"])
                    elif k == "aka":
                        content = aka_chat(nmsgs, nsrv["model_id"])
                    elif k == "hb":
                        content = hb_chat(nmsgs, nsrv["model_id"])
                    elif k == "gk":
                        content = gk_chat(nmsgs, nsrv["model_id"])
                    elif k == "gz":
                        content = gz_chat(nmsgs, nsrv["model_id"])
                    elif k == "pi":
                        content = pi_chat(nmsgs, nsrv["model_id"])
                    elif k == "cb":
                        content = cb_chat(nmsgs, nsrv["model_id"])
                    elif k == "ca":
                        content = ca_chat(nmsgs, nsrv["model_id"])
                    elif k == "ac":
                        content = ac_chat(nmsgs, nsrv["model_id"])
                    elif k == "nv":
                        content = nv_chat(nmsgs, nsrv["model_id"])
                    elif k == "al":
                        content = al_chat(nmsgs, nsrv["model_id"])
                    elif k == "aiml":
                        content = aiml_chat(nmsgs, nsrv["model_id"])
                    else:
                        content = pol_chat(nsrv["id"], nmsgs)
                    if content:
                        print(f"[API] ✅ نەوەی نوێ وەڵامی دا: {up}", flush=True)
            except Exception as e2:
                print(f"[API] دیلی نەوە شکستی هێنا: {str(e2)[:90]}", flush=True)
        if not content:
            return self._send(502, {"error": str(last_err) if last_err else "هیچ سەرچاوەیەک وەڵام نەدایەوە"})

        cid = "chatcmpl-" + "".join(random.choices("abcdef0123456789", k=12))
        now = int(time.time())
        if want_stream:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            def sse(obj):
                self.wfile.write(b"data: " + json.dumps(obj, ensure_ascii=False).encode("utf-8") + b"\n\n")
                self.wfile.flush()

            for i in range(0, len(content), 80):
                sse({"id": cid, "object": "chat.completion.chunk", "created": now,
                     "model": srv["id"],
                     "choices": [{"index": 0, "delta": {"content": content[i:i+80]}, "finish_reason": None}]})
            sse({"id": cid, "object": "chat.completion.chunk", "created": now,
                 "model": srv["id"],
                 "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
            self.wfile.write(b"data: [DONE]\n\n")
        elif openai_style:
            self._send(200, {
                "id": cid, "object": "chat.completion", "created": now, "model": srv["id"],
                "choices": [{"index": 0,
                             "message": {"role": "assistant", "content": content},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            })
        else:
            self._send(200, {"answer": content, "server": srv["id"]})


def start_api():
    """دەستپێکردنی سێرڤەری API لە تڕێدێکی جیاواز"""
    socketserver.ThreadingTCPServer.allow_reuse_address = True

    class TS(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True

    try:
        srv = TS(("0.0.0.0", API_PORT), APIHandler)
    except OSError as e:
        print(f"[API] پۆرتی {API_PORT} بەکارهاتووە: {e}", flush=True)
        return
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"[API] ✅ API کارا کەوت — http://0.0.0.0:{API_PORT} (/v1/chat/completions)", flush=True)


# ════════════════════════════════════════════════════════════
# ٥) تێلەگرام
# ════════════════════════════════════════════════════════════

import os
TOKEN = os.environ.get("BOT_TOKEN") or "8664695955:AAElPxr8spsa--KqsAzHG6Pa4FWnjBmBPQc"
API = f"https://api.telegram.org/bot{TOKEN}"

WELCOME = (
    "🤖 <b>أهلا بك! أنا بوت الدكتور التعافي</b>\n\n"
    "أنا معك خطوة بخطوة في رحلة التعافي — اكتب أي شيء وسأسمعك\n\n"
    "🔹 <b>الأوامر:</b>\n"
    "/new — محادثة جديدة\n"
    "/server — قائمة الموديلات (الأحدث دائما)\n"
    "/about — معلومات عن البوت"
)

ABOUT = (
    "ℹ️ <b>عن هذا البوت</b>\n\n"
    "بوت الدكتور التعافي — مستشار نفسي وشرعي لمساعدتكم على التعافي من الإدمان\n\n"
    "🛡 <b>الخصوصية</b>\n"
    "كل محادثاتكم محفوظة ومشفرة ولا يمكن لأحد الاطلاع عليها حتى مالك البوت نفسه لا يستطيع رؤيتها\n\n"
    "👤 صُنع بواسطة: <b>يوسف الكردي</b>\n"
    "❤️ لخدمة المدمنين على الإباحة وعادة الاستمناء\n\n"
    "🤖 /server — قائمة الموديلات\n"
    "💬 /new — محادثة جديدة"
)

# ژووری گفتوگۆی هەر بەکارهێنەرێک
sessions = {}   # user → {"server": id, "history": [...]}
pending = {}    # user → {"1": server, ...}
BRAIN = {"mode": None, "servers": []}

# دەستنیشانکردنی لێکدانی ناوی مۆدێڵ — هەرگیز ناوی مۆدێڵ ناکرێتەوە
_LEAK_NORM = str.maketrans({"ي": "ی", "ێ": "ی", "ى": "ی", "ك": "ک"})
LEAK_RE = re.compile(r"\b(glm|gpt|claude|gemini|deepseek|qwen|llama|grok|kimi|mistral)[\w.\-]*\b|o4[\s\-]?mini|\bzerotwo\b|zero\s?two|\bquillbot\b|\bduckai\b|duck\s*\.?\s*ai\b|\banakin\b|ئەنەکین|\bnotegpt\b|\bllm7\b|\bg4f\b|\bchattide\b|\byollo\b|\bheck\b|\bhuggingface\b|\bakash\b|\bhotbot\b|\bgadegetkit\b|\bgiz\b|pi\.ai|chatbotapp|chatbotai|askaichat|novaapp|allchatbots|aimlapi|نۆت\s?جی\s?پی\s?تی|(قوین|جی\s*بی\s*تی|جیمینی|دیب\s*سیک|کلود|میسترال|زێرۆ\s?تۆ|کویل|داک)\s*\d*", re.I)


def leaks(s):
    return bool(LEAK_RE.search(str(s).translate(_LEAK_NORM)))
_lock = threading.Lock()


def tg(method, **params):
    try:
        r = requests.post(f"{API}/{method}", json=params, timeout=(15, 25))
        return r.json()
    except Exception as e:
        print(f"[TG] {method}: {e}", flush=True)
        return {"ok": False, "description": str(e)}


def detect_brain(allow_fallback=True):
    """هەر دوو سێرڤەرەکە تێکەڵ بۆ بۆت — easemate + aifreeforever + pollinations — مۆدێل ئایدی ڕاستەقینە"""
    servers = []
    try:
        servers += em_servers()
    except Exception as e:
        print(f"[BRAIN] em fail: {e}", flush=True)
    try:
        for x in get_aff_servers(hide=False):
            y = dict(x); y["kind"] = "aff"; servers.append(y)
    except Exception:
        pass
    try:
        servers.append({"id": "cbc-gpt5", "name": "GPT-5", "kind": "cbc"})
    except Exception:
        pass
    try:
        servers += rwd_servers()
    except Exception as e:
        print(f"[BRAIN] rwd fail: {e}", flush=True)
    try:
        servers += act_servers()
    except Exception as e:
        print(f"[BRAIN] act fail: {e}", flush=True)
    try:
        servers += fla_servers()
    except Exception as e:
        print(f"[BRAIN] fla fail: {e}", flush=True)
    try:
        servers += z02_servers()
    except Exception as e:
        print(f"[BRAIN] z02 fail: {e}", flush=True)
    try:
        servers += qb_servers()
    except Exception as e:
        print(f"[BRAIN] qb fail: {e}", flush=True)
    try:
        servers += duck_servers()
    except Exception as e:
        print(f"[BRAIN] duck fail: {e}", flush=True)
    try:
        servers += ak_servers()
    except Exception as e:
        print(f"[BRAIN] ak fail: {e}", flush=True)
    try:
        servers += ng_servers()
        sync_l7_models()
        servers += l7_servers()
        servers += _g4f_models()
        sync_ct_models()
        servers += ct_servers()
        sync_yl_models()
        servers += yl_servers()
        sync_hk_models()
        servers += hk_servers()
        sync_hf_models()
        servers += hf_servers()
        sync_akash_models()
        servers += aka_servers()
        sync_hb_models()
        servers += hb_servers()
        sync_gk_models()
        servers += gk_servers()
        sync_giz_models()
        servers += gz_servers()
        sync_pi_models()
        servers += pi_servers()
        sync_cb_models()
        servers += cb_servers()
        sync_ca_models()
        servers += ca_servers()
        sync_ac_models()
        servers += ac_servers()
        sync_nv_models()
        servers += nv_servers()
        sync_al_models()
        servers += al_servers()
        sync_aiml_models()
        servers += aiml_servers()
    except Exception as e:
        print(f"[BRAIN] ng fail: {e}", flush=True)
    # ئۆتۆ-سینک — ئەگەر سەرچاوەیەک مۆدێڵی نوێ زیاد کردبێت یان گۆڕیبێت
    try:
        sync_l7_models()
        sync_ct_models()
        sync_yl_models()
        sync_hk_models()
        sync_hf_models()
        sync_akash_models()
        sync_hb_models()
        sync_gk_models()
        sync_giz_models()
        sync_pi_models()
        sync_cb_models()
        sync_ca_models()
        sync_ac_models()
        sync_nv_models()
        sync_al_models()
        sync_aiml_models()
        sync_duck_models(servers)
    except Exception as e:
        print(f"[SYNC] duck fail: {e}", flush=True)
    try:
        sync_ak_models(servers)
    except Exception as e:
        print(f"[SYNC] ak fail: {e}", flush=True)
    servers = _apply_model_sync(servers)
    # pol هەمیشە لە زنجیرەکەدا بێت — لێگی کۆتایی (نەک تەنها فەڵباکی کۆتایی)
    try:
        pol_list = get_pol_servers()
        if pol_list:
            for x in pol_list:
                y = dict(x); y["kind"] = "pol"; servers.append(y)
    except Exception:
        pass
    if servers:
        return {"mode": "multi", "servers": servers}
    return {"mode": None, "servers": []}


def auto_refresh():
    """هەر ٥ خولەک لیستی سێرڤەرەکان نوێ دەکاتەوە —
    هەر مۆدەڵێکی نوێ لە ماڵپەرەکە خۆکارانە دەچێتە ناو سیستەمەکە"""
    while True:
        time.sleep(300)
        try:
            new = detect_brain(allow_fallback=False)
            if not new["servers"]:
                continue  # ماڵپەرەکە کاتییەکە بەردەست نییە — دۆخی ئێستا بمێنێتەوە
            with _lock:
                changed = (new["mode"] != BRAIN["mode"] or
                           [x["id"] for x in new["servers"]] != [x["id"] for x in BRAIN["servers"]])
                BRAIN["mode"], BRAIN["servers"] = new["mode"], new["servers"]
                rebuild_aliases(new["servers"])
                valid = {x["id"] for x in new["servers"]}
                reborn = 0
                for s in sessions.values():
                    if s["server"] not in valid:
                        # ١. هەمان مۆدێڵ لە سەرچاوەیەکی تر — کلیل + نەخشەی سەرچاوەکان
                        old_key = SRV_KEY_BY_ID.get(s["server"]) or s.get("mkey") or norm_model(s["server"])
                        alts = [x for x in MODEL_SOURCES.get(old_key, []) if x["id"] in valid]
                        if alts:
                            s["server"] = alts[0]["id"]
                            s["mkey"] = old_key
                            continue
                        mk = s.get("mkey") or old_key
                        rebind = next((x["id"] for x in new["servers"] if srv_key(x) == mk or norm_model(x["id"]) == mk), None)
                        if rebind:
                            s["server"] = rebind
                            continue
                        # ٢. دیلی نەوە — مۆدێڵەکە لابرا → نوێترین نەوەی هەمان خێزان
                        up = smart_rebind(new["servers"], s["server"])
                        if up:
                            s["server"] = up
                            s["mkey"] = SRV_KEY_BY_ID.get(up) or norm_model(up)
                            reborn += 1
                if reborn:
                    print(f"[REFRESH] 🔄 {reborn} سێشن بۆ نەوەی نوێتر نەقڵکران", flush=True)
            if changed:
                print(f"[REFRESH] ✨ لیستەکە نوێکرایەوە — {new['mode']} ({len(new['servers'])} سێرڤەر)", flush=True)
        except Exception as e:
            print(f"[REFRESH] هەڵە: {e}", flush=True)


# ─── یەکخستنی مۆدێلە دووبارەکان — هەمان مۆدێڵ لە چەند سەرچاوە = یەک دەنگ ───
_MERGE_SUFFIXES = ("-orbio", "-0731", "-0813", "-preview")


def norm_model(mid):
    """کلیلێکی یەکگر بۆ ناسینی هەمان مۆدێڵ لە سەرچاوەی جیاواز"""
    s = str(mid).lower().strip()
    if "/" in s:
        s = s.split("/")[-1]
    s = s.replace("_", "-").replace(".", "-")
    for suf in _MERGE_SUFFIXES:
        if s.endswith(suf):
            s = s[:-len(suf)]
    return s


def srv_key(x):
    """کلیلی سیمانتیکی مۆدێڵ — بۆ گروپکردنی هەمان مۆدێڵ لە سەرچاوەی جیاواز
       model_id ی دەقی (نموونە: gpt-5.6-luna) → کلیلی هاوبەش؛ ژمارەی/نەبوون → id"""
    mid = str(x.get("model_id") or "").strip()
    if not mid or mid.isdigit():
        mid = x["id"]
    return norm_model(mid)


# نەخشەی مۆدێڵ → هەموو سەرچاوەکانی (بۆ فەڵباکی ڕاستەوخۆی هەمان مۆدێڵ)
MODEL_SOURCES = {}
SRV_KEY_BY_ID = {}


def rebuild_aliases(servers):
    """MODEL_SOURCES نوێ دەکاتەوە — مۆدێڵ → لیستی هەموو سەرچاوەکانی بە ڕیز"""
    MODEL_SOURCES.clear()
    SRV_KEY_BY_ID.clear()
    for x in servers:
        k = srv_key(x)
        SRV_KEY_BY_ID[x["id"]] = k
        MODEL_SOURCES.setdefault(k, []).append(x)


def dedupe_servers(servers):
    """یەکێک بۆ هەر مۆدێڵ — یەکەم سەرچاوە سەرەکییە؛ دووەکییەکان لە model_sources دەمێننەوە"""
    rebuild_aliases(servers)
    seen = set()
    uniq = []
    for x in servers:
        k = srv_key(x)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(x)
    return uniq


# ════════════════════════════════════════════════════════════
# ٢.٨) نەوەکان — دەزانی «نوێترین» ی هەر خێزانێک کامەیە
#      بۆ دیل ی خۆکاری: مۆدێڵی نامۆ → نوێترین نەوەی هەمان خێزان
# ════════════════════════════════════════════════════════════

import re as _re

# خشتەی نەوە — بەرزتر = نوێتر (خێزان → لیستی دوایینی بەشەکانی ژمارە)
_GEN_VERSIONS = {
    "gemini": [("3.8", [3, 8]), ("3.6", [3, 6]), ("3.5", [3, 5]), ("3.1", [3, 1]), ("3", [3]), ("2.5", [2, 5]), ("2", [2]), ("1.5", [1, 5])],
    "claude": [("5", [5]), ("4.8", [4, 8]), ("4.7", [4, 7]), ("4.6", [4, 6]), ("4.5", [4, 5]), ("4.1", [4, 1]), ("4", [4]), ("3.7", [3, 7]), ("3.5", [3, 5])],
    "gpt": [("5.6", [5, 6]), ("5.5", [5, 5]), ("5.4", [5, 4]), ("5.2", [5, 2]), ("5.1", [5, 1]), ("5", [5]), ("4.1", [4, 1]), ("4o", [4]), ("4", [4])],
    "grok": [("4.6", [4, 6]), ("4.5", [4, 5]), ("4.3", [4, 3]), ("4", [4]), ("3", [3])],
    "deepseek": [("v4.1", [4, 1]), ("v4", [4]), ("v3.2", [3, 2]), ("r1", [1]), ("v3", [3])],
    "qwen": [("3.8", [3, 8]), ("3.7", [3, 7]), ("3.6", [3, 6]), ("3.5", [3, 5]), ("3", [3]), ("2.5", [2, 5])],
    "glm": [("5.3", [5, 3]), ("5.2", [5, 2]), ("5.1", [5, 1]), ("5", [5]), ("4.7", [4, 7]), ("4.5", [4, 5])],
    "kimi": [("k2.6", [2, 6]), ("k2.5", [2, 5]), ("k2", [2])],
    "llama": [("4", [4]), ("3.3", [3, 3]), ("3.2", [3, 2]), ("3.1", [3, 1]), ("3", [3])],
    "nova": [("2", [2]), ("1", [1])],
    "phi": [("4", [4]), ("3", [3])],
    "hy3": [("4", [4]), ("3", [3])],
    "gemma": [("4", [4]), ("3", [3]), ("2", [2])],
}


def _gen_key(mid):
    """(خێزان، ژمارەی نەوە) — بۆ ڕیزکردن. بۆ نموونە gemini-3.8 → ('gemini', 3.8)"""
    s = str(mid).lower()
    fam = _model_family(s)
    ver = None
    if fam in _GEN_VERSIONS:
        nums = _re.findall(r"(\d+(?:\.\d+)?)", s)
        if nums:
            try:
                ver = float(nums[0])
            except ValueError:
                ver = None
    return (fam, ver if ver is not None else 0.0)


def _same_gen(a, b):
    """ئایا ئەم دوو مۆدێڵە هەمان نەوەن؟ (خێزان + ژمارەی سەرەکی یەکسان)"""
    fa, va = _gen_key(a)
    fb, vb = _gen_key(b)
    if fa != fb:
        return False
    if va == vb:
        return True
    # 3 و 3.0 و 3.8 → بەراوردی ژمارەی سەرەکی
    return int(va) == int(vb)


def _newest_in_family(servers, fam, exclude_id=None):
    """نوێترین مۆدێڵی زیندووی خێزانێک (کار دەکات + ئێستا لە لیستەکەدا هەیە)"""
    best, best_v = None, -1.0
    for x in servers:
        if exclude_id and x["id"] == exclude_id:
            continue
        f, v = _gen_key(x["id"])
        if f == fam and v > best_v:
            best, best_v = x, v
    return best


def _gen_upgrade_candidates(servers, dead_id):
    """کاندیدەکانی دیل بۆ مۆدێڵێکی مردوو: هەمان نەوە یان نوێتر، لە هەمان خێزان،
       ڕیزکراو بە نوێترین. هەرگیز مۆدێڵی کۆنتر نادات."""
    fam, dead_v = _gen_key(dead_id)
    cands = []
    for x in servers:
        f, v = _gen_key(x["id"])
        if f == fam and v >= dead_v:
            if x["id"] != dead_id and x not in cands:
                cands.append(x)
    cands.sort(key=lambda x: _gen_key(x["id"])[1], reverse=True)
    if not cands:
        nx = _newest_in_family(servers, fam)
        if nx:
            cands.append(nx)
    return cands


def smart_rebind(servers, dead_id):
    """دیلی زیرەک: مۆدێڵێکی نامۆ → نوێترین هەمان نەوە/نوێتر لە هەمان خێزان.
       ئەگەر هیچ نەبوو → None (پاشان فەڵباکی ئاسایی)."""
    if not dead_id:
        return None
    for c in _gen_upgrade_candidates(servers, dead_id):
        return c["id"]
    return None


def get_session(user_id):
    with _lock:
        s = sessions.get(user_id)
        if s is None:
            default = BRAIN["servers"][0]["id"] if BRAIN["servers"] else "openai"
            dflt = next((x for x in BRAIN["servers"] if x["id"] == default), None)
            s = {"server": default, "history": [], "mkey": (srv_key(dflt) if dflt else (norm_model(default) if default else None))}
            sessions[user_id] = s
        return s


def ask(session, question):
    """پرسیار — مۆدێڵی هەڵبژارد + زنجیرەی fallback: easemate → aifreeforever → pollinations"""
    history = session["history"]
    sys_msg = {"role": "system", "content": SYSTEM_PROMPT}
    srv = next((x for x in BRAIN["servers"] if x["id"] == session["server"]), None)
    if not srv and BRAIN["servers"]:
        # ١. هەمان مۆدێڵ لە سەرچاوەیەکی تر — بە کلیلی سیمانتیکی مۆدێڵ
        mk = session.get("mkey") or SRV_KEY_BY_ID.get(session.get("server") or "") or norm_model(session.get("server") or "")
        if mk:
            srv = next((x for x in BRAIN["servers"] if srv_key(x) == mk or norm_model(x["id"]) == mk), None)
            if srv:
                session["server"] = srv["id"]
    if not srv and BRAIN["servers"]:
        # ٢. هاوشێوەترین بەپێی خێزان — بەڵام هەڵبژاردەکە ناگۆڕدرێت
        fam = _model_family(session.get("server") or "")
        srv = pick_in_kind(BRAIN["servers"], fam, session.get("server") or "gpt") if fam else None
        if not srv:
            srv = BRAIN["servers"][0]
    order = []
    if srv:
        order.append(srv)
        # ⚡ فەڵباکی خێرا: هەمان مۆدێڵ لە سەرچاوەی تر — پێش هەر شتێکی تر
        for alt in MODEL_SOURCES.get(srv_key(srv), []):
            if alt["id"] != srv["id"] and alt not in order:
                order.append(alt)
    for kind in ("em", "aff", "cbc", "rwd", "l7", "g4f", "pol"):
        if srv and srv.get("kind") == kind:
            continue
        cand = pick_in_kind(BRAIN["servers"], kind, srv["id"] if srv else "gpt")
        if cand and cand not in order:
            order.append(cand)
    last = None
    for cand in order:
        try:
            k = cand.get("kind")
            if k == "em":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                return em_chat(msgs, cand["model_id"]), "em"
            if k == "aff":
                bot = AIFreeChat(model=cand["id"], endpoint=cand.get("endpoint"))
                a = bot.chat(question, history=[sys_msg] + history)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "aff"
            if k == "cbc":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                return cbc_chat(msgs), "cbc"
            if k == "rwd":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = rwd_chat(cand["model_id"], msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "rwd"
            if k == "act":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = act_chat(cand["model_id"], msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "act"
            if k == "fla":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = fla_chat(msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "fla"
            if k == "z02":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = z02_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "z02"
            if k == "qb":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = qb_chat(msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "qb"
            if k == "duck":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = duck_chat(cand["model_id"], msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "duck"
            if k == "ak":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = ak_chat(cand["model_id"], msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "ak"
            if k == "ng":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = ng_chat(msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "ng"
            if k == "l7":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = l7_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "l7"
            if k == "g4f":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = g4f_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "g4f"
            if k == "ct":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = ct_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "ct"
            if k == "yl":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = yl_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "yl"
            if k == "hk":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = hk_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "hk"
            if k == "hf":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = hf_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "hf"
            if k == "aka":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = aka_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "aka"
            if k == "hb":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = hb_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "hb"
            if k == "gk":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = gk_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "gk"
            if k == "gz":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = gz_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "gz"
            if k == "pi":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = pi_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "pi"
            if k == "cb":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = cb_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "cb"
            if k == "ca":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = ca_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "ca"
            if k == "ac":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = ac_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "ac"
            if k == "nv":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = nv_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "nv"
            if k == "al":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = al_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "al"
            if k == "aiml":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = aiml_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "aiml"
            msgs = [sys_msg] + list(history[-20:]) + [{"role": "user", "content": question}]
            return pol_chat(cand["id"], msgs), "pol"
        except Exception as e:
            last = e
            print(f"[BRAIN] {cand.get('kind', '?')} ({cand.get('id', '?')}) هەڵە: {str(e)[:80]}", flush=True)
    # ═══ دیلی نەوە: هەموو زنجیرەکە بۆ ئەم مۆدێڵە مردووە → نوێترین نەوە بپشکنە ═══
    if BRAIN["servers"] and question:
        try:
            dead_id = session.get("server") or ""
            up = smart_rebind(BRAIN["servers"], dead_id)
            if up and up != dead_id:
                nsrv = next(x for x in BRAIN["servers"] if x["id"] == up)
                print(f"[BRAIN] 🔄 دیلی نەوە: {dead_id} → {up}", flush=True)
                k = nsrv.get("kind")
                nmsgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                if k == "em":
                    return em_chat(nmsgs, nsrv["model_id"]), "em"
                if k == "cbc":
                    return cbc_chat(nmsgs), "cbc"
                if k == "rwd":
                    a = rwd_chat(nsrv["model_id"], nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "rwd"
                if k == "act":
                    a = act_chat(nsrv["model_id"], nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "act"
                if k == "fla":
                    a = fla_chat(nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "fla"
                if k == "z02":
                    a = z02_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "z02"
                if k == "qb":
                    a = qb_chat(nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "qb"
                if k == "duck":
                    a = duck_chat(nsrv["model_id"], nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "duck"
                if k == "ak":
                    a = ak_chat(nsrv["model_id"], nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "ak"
                if k == "ng":
                    a = ng_chat(nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "ng"
                if k == "l7":
                    a = l7_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "l7"
                if k == "g4f":
                    a = g4f_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "g4f"
                if k == "ct":
                    a = ct_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "ct"
                if k == "yl":
                    a = yl_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "yl"
                if k == "hk":
                    a = hk_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "hk"
                if k == "hf":
                    a = hf_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "hf"
                if k == "aka":
                    a = aka_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "aka"
                if k == "hb":
                    a = hb_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "hb"
                if k == "gk":
                    a = gk_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "gk"
                if k == "gz":
                    a = gz_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "gz"
                if k == "pi":
                    a = pi_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "pi"
                if k == "cb":
                    a = cb_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "cb"
                if k == "ca":
                    a = ca_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "ca"
                if k == "ac":
                    a = ac_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "ac"
                if k == "nv":
                    a = nv_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "nv"
                if k == "al":
                    a = al_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "al"
                if k == "aiml":
                    a = aiml_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "aiml"
                return pol_chat(nsrv["id"], nmsgs), "pol"
        except Exception as e2:
            print(f"[BRAIN] دیلی نەوە شکستی هێنا: {str(e2)[:80]}", flush=True)
            last = e2
    raise last or RuntimeError("هیچ مێشکێک بەردەست نییە")


def split_msg(t, n=3900):
    return [t[i:i + n] for i in range(0, len(t), n)]


def keep_typing(chat_id, stop):
    while not stop.is_set():
        tg("sendChatAction", chat_id=chat_id, action="typing")
        stop.wait(4.0)


def reply(chat_id, text):
    r = tg("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML",
           disable_web_page_preview=True)
    if not r.get("ok"):
        for part in split_msg(text):
            tg("sendMessage", chat_id=chat_id, text=part.replace("<", "&lt;"))


def handle_message(msg):
    chat_id = msg["chat"]["id"]
    user_id = msg.get("from", {}).get("id", chat_id)
    text = (msg.get("text") or "").strip()
    if not text:
        return

    print(f"[MSG] user={user_id}: {text[:60]}", flush=True)

    if text.startswith("/start"):
        reply(chat_id, WELCOME)
        return
    if text.startswith("/about"):
        reply(chat_id, ABOUT)
        return
    if text.startswith("/new"):
        get_session(user_id)["history"].clear()
        reply(chat_id, "✨ <b>بدأنا محادثة جديدة</b>\nاكتب رسالتك وسنبدأ خطوة بخطوة")
        return

    if text.startswith("/server"):
        reply(chat_id, "🔄 <b>يتم جلب أحدث قائمة…</b>")
        new = detect_brain()
        if not new["servers"]:
            reply(chat_id, "⚠️ <b>تعذر جلب القائمة.</b> حاول بعد قليل.")
            return
        with _lock:
            BRAIN["mode"], BRAIN["servers"] = new["mode"], new["servers"]
        rebuild_aliases(new["servers"])
        servers = new["servers"]
        s = get_session(user_id)
        if s["server"] not in [x["id"] for x in servers]:
            s["server"] = servers[0]["id"]
        # مۆدێلە دووبارەکان یەک دەخرێن — هەمان مۆدێڵ لە چەند سەرچاوە = یەک دەنگ
        uniq = dedupe_servers(servers)
        with _lock:
            pending[user_id] = {str(i): {"id": x["id"], "key": srv_key(x)} for i, x in enumerate(uniq, 1)}
        body = f"🤖 <b>قائمة الموديلات</b> — {len(uniq)} موديل (المكرر بين المصادر مدموج):\n\n"
        for i, x in enumerate(uniq, 1):
            mark = " ✅" if x["id"] == s["server"] else ""
            body += f"{i}. <code>{x['id']}</code>{mark}\n"
        body += "\n✍️ اكتب رقم الموديل فقط للتبديل مثال: <code>5</code>"
        reply(chat_id, body)
        return

    # هەڵبژاردنی سێرڤەر بە ژمارە
    s = get_session(user_id)
    if text.isdigit():
        p = pending.get(user_id)
        if not p:
            reply(chat_id, "🤖 اكتب <code>/server</code> أولا لعرض قائمة الموديلات.")
            return
        if str(int(text)) not in p:
            reply(chat_id, f"⚠️ اكتب رقما بين <code>1</code> و <code>{len(p)}</code>.")
            return
        srv = p[str(int(text))]
        s["server"] = srv["id"]
        s["mkey"] = srv["key"]
        s["history"].clear()
        reply(chat_id, f"✅ تم التبديل إلى الموديل <code>{srv['id']}</code> بنجاح")
        return

    # پرسیاری ئاسایی
    if not BRAIN["servers"]:
        new = detect_brain()
        BRAIN["mode"], BRAIN["servers"] = new["mode"], new["servers"]
        rebuild_aliases(new["servers"])
        if not BRAIN["servers"]:
            reply(chat_id, "⚠️ لا يوجد مصدر متاح الآن — حاول بعد قليل.")
            return
        s["server"] = BRAIN["servers"][0]["id"]

    stop = threading.Event()
    threading.Thread(target=keep_typing, args=(chat_id, stop), daemon=True).start()

    result = {}

    def work():
        try:
            result["answer"] = ask(s, text)
        except Exception as e:
            result["error"] = str(e)

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(timeout=150)

    try:
        if "error" in result:
            answer = f"⚠️ <b>حدث خطأ:</b> {result['error']}\nحاول بعد قليل."
        elif "answer" not in result:
            answer = "⏳ <b>تأخر الرد كثيرا.</b> أعد الإرسال من فضلك."
        else:
            answer, mode = result["answer"]
            if answer:
                s["history"].append({"role": "user", "content": text})
                s["history"].append({"role": "assistant", "content": answer})
                s["history"] = s["history"][-20:]
            else:
                answer = "⚠️ لم يصل رد — حاول مرة أخرى."
    finally:
        stop.set()

    print(f"[ANS] user={user_id}: {len(answer)} chars", flush=True)
    for part in split_msg(answer):
        reply(chat_id, part)


def setup_commands():
    """فەرمانەکانی مێنیو — لەگەڵ دووبارەهەوڵ (تا هەرگیز ون نەبن)"""
    cmds = [
        {"command": "start", "description": "بدء المحادثة مع البوت"},
        {"command": "new", "description": "محادثة جديدة"},
        {"command": "server", "description": "قائمة الموديلات — الأحدث دائما"},
        {"command": "about", "description": "معلومات عن البوت"},
    ]
    # فەرمانەکان لە هەموو سکۆپەکاندا دانراو — تا فەرمانی کۆنی هیچ سیستەمێکی تر ون نەمێنێت
    scopes = [
        {"type": "default"},
        {"type": "all_private_chats"},
        {"type": "all_group_chats"},
    ]
    for attempt in range(3):
        ok = True
        for sc in scopes:
            r = tg("setMyCommands", commands=cmds, scope=sc)
            if not r.get("ok"):
                ok = False
                print(f"[CMDS] {sc.get('type')} شکستی هێنا", flush=True)
        if ok:
            print("✅ فەرمانەکانی مێنیو لە هەموو سکۆپەکان دانران", flush=True)
            return
        print(f"[CMDS] هەوڵ {attempt+1} — دووبارە…", flush=True)
        time.sleep(2)


def start_hf_keepalive():
    """سێرڤەری بچووک + خۆپینگ — بۆ Hugging Face و Render (بۆ نەخەوتن)"""
    import os
    sid = os.environ.get("SPACE_ID")          # Hugging Face
    ext_url = os.environ.get("RENDER_EXTERNAL_URL")  # Render
    if not sid and not ext_url:
        return
    import http.server
    import socketserver
    port = int(os.environ.get("APP_PORT", 7860))

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("🤖 بۆتەکە زیندووە".encode("utf-8"))

        def log_message(self, *a):
            pass

    def serve():
        try:
            socketserver.TCPServer.allow_reuse_address = True
            with socketserver.TCPServer(("0.0.0.0", port), H) as s:
                s.serve_forever()
        except Exception as e:
            print(f"[KEEP] serve: {e}", flush=True)

    threading.Thread(target=serve, daemon=True).start()
    url = ext_url or f"https://{sid.replace('/', '-').lower()}.hf.space"
    where = "Render" if ext_url else "Hugging Face"

    def ping():
        while True:
            time.sleep(840)  # ١٤ خولەک
            try:
                requests.get(url, timeout=15)
            except Exception:
                pass

    threading.Thread(target=ping, daemon=True).start()
    print(f"[KEEP] خۆپینگی {where} لەسەر {url}", flush=True)


def _self_update_daemon():
    """خۆ-نوێکردنەوە لە GitHub raw — هەر ١٠ خولەک؛ تەنها ئەگەر کۆدە نوێیە py_compile تێپەڕێت"""
    import sys as _s, time as _t, subprocess as _sp
    url = "https://raw.githubusercontent.com/Yusfkarim/ayai/main/main.py"
    local = os.path.abspath(__file__)
    while True:
        _t.sleep(600)
        try:
            r = requests.get(url, timeout=(10, 30), headers={"User-Agent": "selfupdater"})
            if r.status_code != 200:
                continue
            new = r.text
            if "def main(" not in new:
                continue
            try:
                cur = open(local, encoding="utf-8").read()
            except Exception:
                continue
            if new == cur:
                continue
            tmp = local + ".new"
            open(tmp, "w", encoding="utf-8").write(new)
            if _sp.run([_s.executable, "-m", "py_compile", tmp], capture_output=True).returncode != 0:
                try:
                    os.remove(tmp)
                except Exception:
                    pass
                continue
            os.replace(tmp, local)
            print("[SELF-UPDATE] کۆدی نوێ لە GitHub — ریستارت…", flush=True)
            _t.sleep(2)
            os.execv(_s.executable, [_s.executable] + _s.argv)
        except Exception:
            continue


def main():
    print("🔄 دەستپێکردنی بۆتی تێلەگرام…", flush=True)
    threading.Thread(target=_self_update_daemon, daemon=True).start()
    start_api()          # 🔌 API — بۆ بەکارهێنان وەک API
    start_hf_keepalive()
    me = tg("getMe")
    if not me.get("ok"):
        print("❌ تۆکن هەڵەیە یان ئینتەرنێت نییە:", me.get("description"), flush=True)
        return
    print(f"✅ بۆت: @{me['result']['username']} ({me['result']['first_name']})", flush=True)

    # کەیک-بەیکەری G4F — پاشبنەما
    threading.Thread(target=_g4f_baker_daemon, daemon=True).start()
    print("🍰 کەیک-بەیکەری G4F چالاکە", flush=True)

    # دەستنیشانکردنی مێشک
    print("🧠 دەستنیشانکردنی سەرچاوەی AI…", flush=True)
    new = detect_brain()
    BRAIN["mode"], BRAIN["servers"] = new["mode"], new["servers"]
    rebuild_aliases(new["servers"])
    if new["mode"] == "aff":
        print(f"🟢 مێشکی سەرەکی: aifreeforever ({len(new['servers'])} سێرڤەر)", flush=True)
    elif new["mode"] == "pol":
        print(f"🟡 مێشکی جێگرەوە: pollinations ({len(new['servers'])} سێرڤەر)", flush=True)
    else:
        print("⚠️ هیچ سەرچاوەیەک نەدۆزرایەوە — دواتر دووبارە هەوڵ دەدرێتەوە", flush=True)

    tg("deleteWebhook")
    setup_commands()
    # 🔄 چاودێری لیستی مۆدەڵەکان — هەر ٥ خولەک
    threading.Thread(target=auto_refresh, daemon=True).start()
    print("🟢 بۆت کارا کەوت — چاوەڕێی نامەکانە…", flush=True)

    offset = 0
    cycle = 0
    while True:
        try:
            cycle += 1
            if cycle % 10 == 1:
                print(f"[LOOP] زیندووە — cycle {cycle}, offset={offset}", flush=True)

            r = tg("getUpdates", offset=offset, timeout=8, allowed_updates=["message"])
            if not r.get("ok"):
                print(f"[POLL] ok=false: {r.get('description', '?')}", flush=True)
                time.sleep(3)
                continue
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                m = u.get("message")
                if m and m.get("text"):
                    threading.Thread(target=handle_message, args=(m,), daemon=True).start()
                elif m:
                    reply(m["chat"]["id"], "💬 أرسل رسالة نصية من فضلك.")
        except KeyboardInterrupt:
            print("⏹ وەسترا.", flush=True)
            break
        except Exception as e:
            print(f"[POLL] هەڵە: {e}", flush=True)
            time.sleep(3)


if __name__ == "__main__":
    main()
