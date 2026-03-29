from flask import Flask, request, jsonify
import requests
import random

app = Flask(__name__)

# روابط الخلفية والأصوات
BG_URL = "https://img.freepik.com/premium-photo/dark-islamic-background-with-mosque-silhouette-golden-ornaments_1130458-3850.jpg"
PROPHET_AUDIO = "https://f.top4top.io/m_2402v3u0l1.mp3" 
AZAN_AUDIO = "https://www.islamcan.com/audio/adan/azan1.mp3" 

def format_time(t24):
    try:
        h, m = map(int, t24.split(':')); p = "ص" if h < 12 else "م"; h = h % 12
        if h == 0: h = 12
        return f"{h}:{m:02d} {p}"
    except: return t24

# سكريبت البحث + نظام التنبيهات + نظام الأذان
auto_scripts = '''
<script>
function filterItems() {
    var input = document.getElementById("searchInput").value.trim().toLowerCase();
    var items = document.getElementsByClassName("list-item-wrapper");
    for (var i = 0; i < items.length; i++) {
        var btn = items[i].getElementsByClassName("list-item")[0];
        var name = btn.getAttribute("data-name").toLowerCase();
        var num = btn.getAttribute("data-num") || "";
        if (name.includes(input) || num === input) {
            items[i].style.display = "block";
        } else {
            items[i].style.display = "none";
        }
    }
}

var prophetAudio = new Audio("''' + PROPHET_AUDIO + '''");
var azanAudio = new Audio("''' + AZAN_AUDIO + '''");
var isProphetEnabled = false;
var isAzanEnabled = false;
var prophetTimer = null;

function toggleAzan() {
    var btn = document.getElementById('azanBtn');
    if (!isAzanEnabled) {
        azanAudio.play().then(() => {
            azanAudio.pause(); azanAudio.currentTime = 0;
            isAzanEnabled = true;
            btn.innerHTML = "✅ تم تفعيل الأذان في جميع الصلوات";
            btn.style.background = "#27ae60";
            alert("✅ تم تفعيل صوت الأذان تلقائياً");
        }).catch(e => alert("❌ فشل تفعيل الأذان"));
    } else {
        isAzanEnabled = false;
        btn.innerHTML = "🕋 اضغط لتفعيل الأذان في جميع الصلوات";
        btn.style.background = "#2980b9";
        alert("⚠️ تم إيقاف صوت الأذان");
    }
}

function toggleProphet() {
    var btn = document.getElementById('audioBtn');
    if (!isProphetEnabled) {
        prophetAudio.play().then(() => {
            prophetAudio.pause(); prophetAudio.currentTime = 0;
            isProphetEnabled = true;
            btn.innerHTML = "✅ تم تفعيل تنبيهات الصلاة على النبي";
            btn.style.background = "#27ae60";
            prophetTimer = setInterval(function() { prophetAudio.currentTime = 0; prophetAudio.play(); }, 3600000);
            alert("✅ تم تفعيل التنبيه كل ساعة");
        }).catch(e => alert("❌ فشل التفعيل"));
    } else {
        clearInterval(prophetTimer);
        isProphetEnabled = false;
        btn.innerHTML = "🔔 اضغط هنا لتفعيل تنبيه الصلاة على النبي";
        btn.style.background = "#f39c12";
        alert("⚠️ تم إيقاف التنبيهات");
    }
}
</script>
'''

STYLE = f'''<style>
    body {{ background: url("{BG_URL}") no-repeat center center fixed; background-size: cover; color:white; padding:10px; font-family:Arial; direction: rtl; }}
    .container {{ background: rgba(0,0,0,0.85); padding: 15px; border-radius: 20px; min-height: 95vh; display: flex; flex-direction: column; align-items: center; }}
    .btn-main {{ padding:18px; background:#27ae60; color:white; border:none; border-radius:12px; margin:6px; width:95%; font-size:18px; font-weight:bold; cursor: pointer; display: block; text-decoration: none; text-align: center; }}
    .list-item {{ padding:12px; background:#111; border:1px solid #f1c40f; color:white; width:100%; border-radius:8px; font-size:14px; cursor:pointer; text-align:center; display:block; text-decoration:none; font-weight:bold; }}
    .grid-container {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; width: 100%; margin-top:10px; }}
    .hadith-card {{ background: rgba(255,255,255,0.05); padding: 25px; border-radius: 15px; border-right: 8px solid #f1c40f; width: 90%; text-align: right; line-height: 1.8; font-size: 22px; margin-top: 20px; }}
    .alert-btn {{ background:#f39c12; animation: pulse 2s infinite; border: 2px solid #fff; }}
    .azan-btn {{ background:#2980b9; margin-bottom: 10px; border: 2px solid #fff; }}
    @keyframes pulse {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.03); }} 100% {{ transform: scale(1); }} }}
</style>'''

# قاعدة بيانات الأحاديث الـ 20 كاملة
bukhari_data = [
    {"id": 1, "t": "1. حديث النية", "x": "عن عمر بن الخطاب رضي الله عنه قال: سمعت رسول الله ﷺ يقول: (إنما الأعمال بالنيات، وإنما لكل امرئ ما نوى). [رواه البخاري]"},
    {"id": 2, "t": "2. بني الإسلام", "x": "عن ابن عمر رضي الله عنهما قال: قال رسول الله ﷺ: (بني الإسلام على خمس: شهادة أن لا إله إلا الله وأن محمداً رسول الله، وإقام الصلاة، وإيتاء الزكاة، وحج البيت، وصوم رمضان). [رواه البخاري]"},
    {"id": 3, "t": "3. تعلم القرآن", "x": "عن عثمان بن عفان قال: قال النبي ﷺ: (خيركم من تعلم القرآن وعلمه). [رواه البخاري]"},
    {"id": 4, "t": "4. آية المنافق", "x": "قال ﷺ: (آية المنافق ثلاث: إذا حدث كذب، إذا وعد أخلف، وإذا اؤتمن خان). [رواه البخاري]"},
    {"id": 5, "t": "5. بر الوالدين", "x": "سألت النبي أي العمل أحب؟ قال: (الصلاة على وقتها، ثم بر الوالدين). [رواه البخاري]"},
    {"id": 6, "t": "6. يسروا", "x": "قال ﷺ: (يسروا ولا تعسروا، وبشروا ولا تنفروا). [رواه البخاري]"},
    {"id": 7, "t": "7. السواك", "x": "قال ﷺ: (لولا أن أشق على أمتي لأمرتهم بالسواك مع كل صلاة). [رواه البخاري]"},
    {"id": 8, "t": "8. المسلم", "x": "قال ﷺ: (المسلم من سلم المسلمون من لسانه ويده). [رواه البخاري]"},
    {"id": 9, "t": "9. الصدق", "x": "قال ﷺ: (عليكم بالصدق، فإن الصدق يهدي إلى البر). [رواه البخاري]"},
    {"id": 10, "t": "10. المساجد", "x": "قال ﷺ: (من بنى مسجداً يبتغي به وجه الله بنى الله له مثله في الجنة). [رواه البخاري]"}
]
muslim_data = [
    {"id": 11, "t": "11. النصيحة", "x": "عن تميم الداري أن النبي ﷺ قال: (الدين النصيحة). [رواه مسلم]"},
    {"id": 12, "t": "12. الغش", "x": "عن أبي هريرة قال رسول الله ﷺ: (من غشنا فليس منا). [رواه مسلم]"},
    {"id": 13, "t": "13. العلم", "x": "قال ﷺ: (من سلك طريقاً يلتمس فيه علماً سهل الله له به طريقاً إلى الجنة). [رواه مسلم]"},
    {"id": 14, "t": "14. الاستقامة", "x": "قال رسول الله ﷺ: (قل آمنت بالله ثم استقم). [رواه مسلم]"},
    {"id": 15, "t": "15. فضل القرآن", "x": "قال ﷺ: (اقرأوا القرآن فإنه يأتي يوم القيامة شفيعاً لأصحابه). [رواه مسلم]"},
    {"id": 16, "t": "16. الظلم", "x": "قال النبي ﷺ: (اتقوا الظلم فإن الظلم ظلمات يوم القيامة). [رواه مسلم]"},
    {"id": 17, "t": "17. الطهور", "x": "قال النبي ﷺ: (الطهور شطر الإيمان). [رواه مسلم]"},
    {"id": 18, "t": "18. الذكر", "x": "قال ﷺ: (لأن أقول سبحان الله والحمد لله أحب إلي مما طلعت عليه الشمس). [رواه مسلم]"},
    {"id": 19, "t": "19. السنة", "x": "قال النبي ﷺ: (من سن في الإسلام سنة حسنة فله أجرها). [رواه مسلم]"},
    {"id": 20, "t": "20. حق المسلم", "x": "قال ﷺ: (حق المسلم على المسلم ست: إذا لقيته فسلم عليه...). [رواه مسلم]"}
]

@app.route('/')
def home():
    return f'''{STYLE}<body dir="rtl"><div class="container">
        <h1 style="text-align:center; font-size: 18px; border: 2px solid #27ae60; padding:10px; border-radius:15px; background: rgba(0,0,0,0.8); width: 90%;">عبد الرحمن شاب مسلم هيساعد المسلمين</h1>
        <button id="azanBtn" class="btn-main azan-btn" onclick="toggleAzan()">🕋 اضغط لتفعيل الأذان في جميع الصلوات</button>
        <button id="audioBtn" class="btn-main alert-btn" onclick="toggleProphet()">🔔 اضغط هنا لتفعيل تنبيه الصلاة على النبي</button>
        <a href="/p_cities" class="btn-main">🕋 مواقيت الصلاة</a>
        <a href="/q_idx/read" class="btn-main" style="background:#2980b9;">📖 المصحف الكريم</a>
        <a href="/q_idx/tafsir" class="btn-main" style="background:#e67e22;">📚 تفسير القرآن</a>
        <a href="/h_main" class="btn-main" style="background:#f1c40f; color:black;">📜 الأحاديث النبوية</a>
        <a href="/t_view" class="btn-main" style="background:#16a085;">📿 السبحة الإلكترونية الذكية</a>
        <a href="/r_list" class="btn-main" style="background:#9b59b6;">🎧 المصحف الصوتي</a>
        <a href="/rd_view" class="btn-main" style="background:#e74c3c;">📻 إذاعة القرآن الكريم</a>
        <div style="text-align:center; margin-top:20px; border-top: 1px solid #555; padding-top:15px; width: 100%;">
            <p style="font-size:15px; font-weight:bold;">فَإِذَا جَاءَ أَمْرُ اللَّهِ قُضِيَ بِالْحَقِّ وَخَسِرَ هُنَالِكَ الْمُبْطِلُونَ</p>
            <p style="font-size:13px; color:#27ae60;">تم تصميم هذا التطبيق لمساعدة المسلمين حول العالم</p>
            <p style="font-size:13px; color:#fff;">تواصل معنا للمساعدة</p>
            <div style="display: flex; justify-content: center; gap: 30px; margin-top: 15px;">
                <a href="https://wa.me/201153297929"><img src="https://cdn-icons-png.flaticon.com/512/733/733585.png" width="45"></a>
                <a href="https://www.facebook.com/share/1DvSFCtmyo/"><img src="https://cdn-icons-png.flaticon.com/512/733/733547.png" width="45"></a>
                <a href="https://youtube.com/channel/UC2k1P03gfQu_Ic759XaeYhw?si=OOfLyQ75zwSyx_rB"><img src="https://cdn-icons-png.flaticon.com/512/1384/1384060.png" width="45"></a>
            </div>
        </div>
    </div>{auto_scripts}</body>'''

@app.route('/h_main')
def h_main():
    return f'{STYLE}<body dir="rtl"><div class="container"><h2 style="color:#27ae60;">📜 كتب السنة</h2><a href="/h_l/b" class="btn-main" style="background:#333; border:1px solid #f1c40f;">صحيح البخاري</a><a href="/h_l/m" class="btn-main" style="background:#333; border:1px solid #f1c40f;">صحيح مسلم</a><a href="/" class="btn-main" style="background:#555;">🏠 الرئيسية</a></div>{auto_scripts}</body>'

@app.route('/h_l/<book>')
def h_l(book):
    items = bukhari_data if book == "b" else muslim_data
    out = '<h2 style="color:#27ae60;">فهرس الأحاديث</h2><input type="text" id="searchInput" onkeyup="filterItems()" placeholder="ابحث باسم أو رقم..." style="padding:12px; width:90%; border-radius:10px; margin-bottom:15px; text-align:right;"><div class="grid-container">'
    for h in items: out += f'<div class="list-item-wrapper"><a href="/h_v/{book}/{h["id"]}" class="list-item" data-name="{h["t"]}" data-num="{h["id"]}">{h["t"]}</a></div>'
    out += f'</div><a href="/h_main" class="btn-main" style="background:#555; width:60%;">⬅ عودة</a>'
    return f'{STYLE}<body dir="rtl"><div class="container">{out}</div>{auto_scripts}</body>'

@app.route('/h_v/<book>/<int:hid>')
def h_v(book, hid):
    items = bukhari_data if book == "b" else muslim_data
    h = next((i for i in items if i["id"] == hid), None)
    return f'{STYLE}<body dir="rtl"><div class="container" style="text-align:right;"><h2 style="color:#f1c40f; width:90%;">{h["t"]}</h2><div class="hadith-card">{h["x"]}</div><a href="javascript:history.back()" class="btn-main" style="background:#333; width:60%;">⬅ عودة</a></div>{auto_scripts}</body>'

@app.route('/q_idx/<mode>')
def q_idx(mode):
    res = requests.get("https://api.alquran.cloud/v1/surah").json(); out = f'<h2 style="color:#27ae60;">الفهرس</h2><input type="text" id="searchInput" onkeyup="filterItems()" placeholder="ابحث..." style="padding:12px; width:90%; border-radius:10px; margin-bottom:20px; text-align: right;"><div class="grid-container">'
    for s in res['data']: out += f'<div class="list-item-wrapper"><a href="/q_view/{mode}/{s["number"]}" class="list-item" data-name="{s["name"]}" data-num="{s["number"]}">{s["number"]}. {s["name"]}</a></div>'
    out += f'</div><a href="/" class="btn-main" style="background:#555; width:60%;">🏠 الرئيسية</a>'
    return f'{STYLE}<body dir="rtl"><div class="container">{out}</div>{auto_scripts}</body>'

@app.route('/q_view/<mode>/<int:num>')
def q_view(mode, num):
    res_q = requests.get(f"https://api.alquran.cloud/v1/surah/{num}").json(); res_t = requests.get(f"https://api.alquran.cloud/v1/surah/{num}/ar.jalalayn").json(); out = f'<h2 style="color:#27ae60; text-align:right; width:95%;">سورة {res_q["data"]["name"]}</h2><div style="background:#fdfcf0; color:#000; padding:20px; border-radius:15px; line-height:2.2; font-size:22px; text-align:right;">'
    for i, a in enumerate(res_q['data']['ayahs']):
        if mode == "read": out += f"{a['text']} <span style='color:#27ae60;'>﴿{i+1}﴾</span> "
        else: out += f"<div style='border-bottom:1px solid #ddd; padding:10px 0;'><b>{a['text']}</b><br><span style='color:#555; font-size:16px;'>{res_t['data']['ayahs'][i]['text']}</span></div>"
    return f'{STYLE}<body dir="rtl"><div class="container">{out}</div><a href="javascript:history.back()" class="btn-main" style="background:#333; width:60%;">⬅ عودة</a></div>{auto_scripts}</body>'

@app.route('/a_play/<code>/<int:num>')
def a_play(code, num):
    s_num = str(num).zfill(3); srvs = {'hussary':'https://server13.mp3quran.net/hussary','basit':'https://server7.mp3quran.net/basit','minsh':'https://server10.mp3quran.net/minsh','afs':'https://server8.mp3quran.net/afs','shur':'https://server7.mp3quran.net/shur','maher':'https://server12.mp3quran.net/maher'}
    return f'''{STYLE}<body dir="rtl"><div class="container" style="text-align:center; padding-top:40px;">
        <h3 style="color:#f1c40f;">سورة رقم {num}</h3>
        <audio id="quranAudio" controls autoplay style="width:100%;"><source src="{srvs[code]}/{s_num}.mp3" type="audio/mpeg"></audio>
        <p style="color:#27ae60; font-weight:bold; margin-top:15px; background:rgba(0,0,0,0.5); padding:10px; border-radius:8px;">⌛ انتظر التحميل أو جرب شيخ آخر</p>
        <a href="javascript:history.back()" class="btn-main" style="width:60%; background:#333;">⬅ عودة للفهرس</a>
    </div>{auto_scripts}</body>'''

@app.route('/p_cities')
def p_cities():
    cities = [('الفيوم','Fayoum'),('القاهرة','Cairo'),('الجيزة','Giza'),('الإسكندرية','Alexandria'),('طنطا','Tanta'),('المنصورة','Mansoura'),('بني سويف','Beni_Suef'),('سوهاج','Sohag'),('المنيا','Minya'),('أسيوط','Asyut'),('الأقصر','Luxor'),('أسوان','Aswan')]; out = '<h2 style="color:#27ae60;">اختر المحافظة</h2><div class="grid-container">'
    for ar, en in cities: out += f'<a href="/pr/{en}/{ar}" style="text-decoration:none;"><button class="list-item" style="background:#333;">{ar}</button></a>'
    return f'{STYLE}<body dir="rtl"><div class="container">{out}<a href="/" class="btn-main" style="background:#555; width:60%;">🏠 الرئيسية</a></div>{auto_scripts}</body>'

@app.route('/pr/<en>/<ar>')
def pr(en, ar):
    res = requests.get(f"http://api.aladhan.com/v1/timingsByCity?city={en}&country=Egypt&method=5").json(); t = res['data']['timings']; out = f"<h2 style='color:#27ae60;'>مواقيت صلاة {ar}</h2>"
    for k, v in {'Fajr':'الفجر','Dhuhr':'الظهر','Asr':'العصر','Maghrib':'المغرب','Isha':'العشاء'}.items(): out += f"<div style='width:95%; font-size:20px; margin:10px; padding:15px; background:rgba(0,0,0,0.8); border-radius:15px; display: flex; justify-content: space-between; border-right: 6px solid #27ae60;'><span>{format_time(t[k])}</span><b>{v}</b></div>"
    return f'{STYLE}<body dir="rtl"><div class="container">{out}<a href="/p_cities" class="btn-main" style="background:#555; width:60%;">⬅ عودة</a></div>{auto_scripts}</body>'

@app.route('/t_view')
def t_view():
    return f'''{STYLE}<body dir="rtl"><div class="container" style="text-align:center;"><h2 style="color:#27ae60;">📿 السبحة الإلكترونية الذكية</h2><div style="font-size:26px; color:#fff; background:rgba(39,174,96,0.4); padding:15px; border-radius:10px; margin-bottom:10px;" id="zekrDisplay">سبحان الله</div><div style="font-size:70px; color:#f1c40f; margin:10px;" id="count">0</div><button class="btn-main" style="background:#27ae60; width:85%; font-size:28px;" onclick="add()">اضغط للذكر</button><button class="btn-main" style="background:#e74c3c; width:40%;" onclick="reset()">تصفير</button><a href="/" class="btn-main" style="background:#555; width:60%;">🏠 الرئيسية</a><script>let c = 0; const azkar = ["سبحان الله", "الحمد لله", "الله أكبر", "لا إله إلا الله"]; function add() {{ c++; document.getElementById('count').innerHTML = c; let index = Math.floor(c / 33) % azkar.length; document.getElementById('zekrDisplay').innerHTML = azkar[index]; }} function reset() {{ c = 0; document.getElementById('count').innerHTML = c; document.getElementById('zekrDisplay').innerHTML = azkar[0]; }}</script></div>{auto_scripts}</body>'''

@app.route('/rd_view')
def rd_view(): return f'{STYLE}<body dir="rtl"><div class="container" style="text-align:center;"><h2>📻 راديو القاهرة</h2><audio controls autoplay style="width:100%;"><source src="https://n04.radiojar.com/8s5u8s3n80zuv" type="audio/mpeg"></audio><a href="/" class="btn-main" style="background:#555; width:60%;">🏠 الرئيسية</a></div>{auto_scripts}</body>'

@app.route('/r_list')
def r_list():
    reciters = [('محمود الحصري','hussary'),('عبد الباسط','basit'),('المنشاوي','minsh'),('العفاسي','afs'),('الشريم','shur'),('ماهر المعيقلي','maher')]; out = '<h2 style="color:#27ae60;">🎧 القراء</h2>'
    for name, code in reciters: out += f'<a href="/a_surahs/{code}/{name}" class="btn-main" style="background:#333; border:1px solid #9b59b6;">الشيخ {name}</a>'
    return f'{STYLE}<body dir="rtl"><div class="container">{out}<a href="/" class="btn-main" style="background:#555; width:60%;">🏠 الرئيسية</a></div>{auto_scripts}</body>'

@app.route('/a_surahs/<code>/<name>')
def a_surahs(code, name):
    res = requests.get("https://api.alquran.cloud/v1/surah").json(); out = f'<h2 style="color:#27ae60;">مصحف {name}</h2><input type="text" id="searchInput" onkeyup="filterItems()" placeholder="ابحث..." style="padding:12px; width:90%; border-radius:10px; margin-bottom:20px; text-align: right;"><div class="grid-container">'
    for s in res['data']: out += f'<div class="list-item-wrapper"><a href="/a_play/{code}/{s["number"]}" class="list-item" data-name="{s["name"]}" data-num="{s["number"]}">{s["number"]}. {s["name"]}</a></div>'
    out += f'</div><a href="javascript:history.back()" class="btn-main" style="background:#555; width:60%;">⬅ عودة</a>'
    return f'{STYLE}<body dir="rtl"><div class="container">{out}</div>{auto_scripts}</body>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
