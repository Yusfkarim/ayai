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
_RWD_STATE = {"sess": None, "t": 0.0}
# ئەوانەی بە دڵنیاییەوە تاقیکرانەوە و لە بودجەی میواندا جێگیرن
_RWD_VERIFIED = [
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
    """سێرڤەرەکانی rewind — پشتڕاستکراوەکان + ئەوانەی ناویان کەم‌خوارەیە (لە بودجە)"""
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
            if len(chosen) >= 24:
                break
    return [{"id": mid, "name": mid, "model_id": mid, "kind": "rwd"} for mid in chosen]


def _rwd_session(timeout=15):
    """سێشنی rewind — GET ی سەرەتا کوکییەی anon_token دەگرێت (پێویستە بۆ POST)"""
    if _RWD_STATE["sess"] is None:
        _RWD_STATE["sess"] = requests.Session()
    if time.time() - _RWD_STATE["t"] > 2000000:
        try:
            _RWD_STATE["sess"].get(RWD_BASE + "/v1/models",
                                   headers={"User-Agent": UA}, timeout=timeout)
            _RWD_STATE["t"] = time.time()
        except Exception:
            pass
    return _RWD_STATE["sess"]


def rwd_chat(model_id, messages, timeout=110):
    """پرسیار بۆ rewind — OpenAI-جۆر، بێ کلیل (تۆکنی نەناسراو خۆکارانە)"""
    s = _rwd_session()
    h = {"User-Agent": UA, "Content-Type": "application/json"}
    r = s.post(RWD_BASE + "/v1/chat/completions/", headers=h,
               json={"model": model_id, "messages": messages}, timeout=(15, timeout))
    if r.status_code == 400:
        # کوکییەکە کۆن/نییە — نوێی بکەوە و دووبارە هەوڵ بدە
        _RWD_STATE["t"] = 0.0
        s2 = _rwd_session()
        r = s2.post(RWD_BASE + "/v1/chat/completions/", headers=h,
                    json={"model": model_id, "messages": messages}, timeout=(15, timeout))
    if r.status_code == 429:
        raise EMError("rwd: ڕێژە زۆرە — چاوەڕێ بکە")
    try:
        j = r.json()
    except Exception:
        raise EMError(f"rwd: {r.status_code}")
    if isinstance(j.get("error"), dict):
        code = str(j["error"].get("code") or "")[:60]
        if code == "INSUFFICIENT_TOKENS":
            raise EMError("rwd: تۆکنی میوان تەواو بوو")
        raise EMError("rwd: " + (code or str(j["error"])[:50]))
    ch = (j.get("choices") or [{}])[0]
    ans = ((ch.get("message") or {}).get("content") or "").strip()
    if not ans:
        raise EMError("rwd: وەڵامی بەتاڵ")
    return ans


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
        API_BRAIN["t"] = time.time()
        print(f"[API-BRAIN] {new['mode']} ({len(new['servers'])} سێرڤەر)", flush=True)


def _api_servers():
    # ناوە ڕاستەقینەکانی مۆدەڵەکان — وەک خۆیان (gemini-3-1، gpt-5-mini، …)
    return [{"alias": x["id"], "id": x["id"], "name": x.get("name", x["id"])}
            for x in API_BRAIN["servers"]]


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
        for kind in ("em", "aff", "cbc", "rwd", "pol"):
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
LEAK_RE = re.compile(r"\b(glm|gpt|claude|gemini|deepseek|qwen|llama|grok|kimi|mistral)[\w.\-]*\b|o4[\s\-]?mini|(قوین|جی\s*بی\s*تی|جیمینی|دیب\s*سیک|کلود|میسترال)\s*\d*", re.I)


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
                valid = {x["id"] for x in new["servers"]}
                for s in sessions.values():
                    if s["server"] not in valid:
                        # بگەڕێ بۆ هەمان مۆدێڵ لە سەرچاوەیەکی تر — هەرگیز مۆدێڵی تر جێگرەوە مەکە
                        mk = s.get("mkey") or norm_model(s["server"])
                        rebind = next((x["id"] for x in new["servers"] if norm_model(x["id"]) == mk), None)
                        if rebind:
                            s["server"] = rebind
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


def dedupe_servers(servers):
    """یەکێک بۆ هەر مۆدێڵ — یەکەم سەرچاوە (easemate) دەبێتە سەرەکی"""
    seen = set()
    uniq = []
    for x in servers:
        k = norm_model(x["id"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(x)
    return uniq


def get_session(user_id):
    with _lock:
        s = sessions.get(user_id)
        if s is None:
            default = BRAIN["servers"][0]["id"] if BRAIN["servers"] else "openai"
            s = {"server": default, "history": [], "mkey": norm_model(default) if default else None}
            sessions[user_id] = s
        return s


def ask(session, question):
    """پرسیار — مۆدێڵی هەڵبژارد + زنجیرەی fallback: easemate → aifreeforever → pollinations"""
    history = session["history"]
    sys_msg = {"role": "system", "content": SYSTEM_PROMPT}
    srv = next((x for x in BRAIN["servers"] if x["id"] == session["server"]), None)
    if not srv and BRAIN["servers"]:
        # ١. هەمان مۆدێڵ لە سەرچاوەیەکی تر
        mk = session.get("mkey") or norm_model(session.get("server") or "")
        if mk:
            srv = next((x for x in BRAIN["servers"] if norm_model(x["id"]) == mk), None)
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
    for kind in ("em", "aff", "cbc", "rwd", "pol"):
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
            msgs = [sys_msg] + list(history[-20:]) + [{"role": "user", "content": question}]
            return pol_chat(cand["id"], msgs), "pol"
        except Exception as e:
            last = e
            print(f"[BRAIN] {cand.get('kind', '?')} ({cand.get('id', '?')}) هەڵە: {str(e)[:80]}", flush=True)
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
        servers = new["servers"]
        s = get_session(user_id)
        if s["server"] not in [x["id"] for x in servers]:
            s["server"] = servers[0]["id"]
        # مۆدێلە دووبارەکان یەک دەخرێن — هەمان مۆدێڵ لە چەند سەرچاوە = یەک دەنگ
        uniq = dedupe_servers(servers)
        with _lock:
            pending[user_id] = {str(i): {"id": x["id"], "key": norm_model(x["id"])} for i, x in enumerate(uniq, 1)}
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


def main():
    print("🔄 دەستپێکردنی بۆتی تێلەگرام…", flush=True)
    start_api()          # 🔌 API — بۆ بەکارهێنان وەک API
    start_hf_keepalive()
    me = tg("getMe")
    if not me.get("ok"):
        print("❌ تۆکن هەڵەیە یان ئینتەرنێت نییە:", me.get("description"), flush=True)
        return
    print(f"✅ بۆت: @{me['result']['username']} ({me['result']['first_name']})", flush=True)

    # دەستنیشانکردنی مێشک
    print("🧠 دەستنیشانکردنی سەرچاوەی AI…", flush=True)
    new = detect_brain()
    BRAIN["mode"], BRAIN["servers"] = new["mode"], new["servers"]
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
