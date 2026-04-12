import os
import requests
import calendar
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
# 需要安装: pip install zhdate
try:
    from zhdate import ZhDate
except ImportError:
    print("提示: 请安装 zhdate 库以支持农历显示")

# ================= 配置区 =================
API_KEY = os.environ.get("ZECTRIX_API_KEY")
MAC_ADDRESS = os.environ.get("ZECTRIX_MAC")
PUSH_URL = f"https://cloud.zectrix.com/open/v1/devices/{MAC_ADDRESS}/display/image"

# 天气代码：101030103 为天津津南区 (天大北洋园校区所在地)
WEATHER_CITY_CODE = "101030103" 

FONT_PATH = "font.ttf"
try:
    font_large = ImageFont.truetype(FONT_PATH, 60) # 大月份
    font_title = ImageFont.truetype(FONT_PATH, 24) # 标题/年份
    font_item = ImageFont.truetype(FONT_PATH, 18)  # 阳历数字
    font_tiny = ImageFont.truetype(FONT_PATH, 12)  # 农历/节日
    font_small = ImageFont.truetype(FONT_PATH, 14) # 星期头
except:
    print("错误: 找不到 font.ttf")
    exit(1)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# ================= 工具函数 =================

def get_lunar_text(y, m, d):
    """获取农历或节日"""
    try:
        date_obj = datetime(y, m, d)
        lunar = ZhDate.from_datetime(date_obj)
        
        # 常见公历节日
        solar_festivals = { (1,1):"元旦", (5,1):"劳动节", (10,1):"国庆节" }
        # 常见农历节日
        lunar_festivals = { (1,1):"春节", (1,15):"元宵", (5,5):"端午", (7,7):"七夕", (8,15):"中秋", (9,9):"重阳" }
        
        # 特殊处理清明 (通常4月4或5日)
        if m == 4 and (d == 4 or d == 5):
            # 简单逻辑：4月4或5日如果是清明节气则显示
            return "清明"

        if (m, d) in solar_festivals: return solar_festivals[(m, d)]
        if (lunar.lunar_month, lunar.lunar_day) in lunar_festivals: return lunar_festivals[(lunar.lunar_month, lunar.lunar_day)]
        
        # 否则显示农历日期（如：初八，廿十）
        return lunar.lunar_date_str().split('年')[1][-2:]
    except:
        return ""

def push_image(img, page_id):
    img.save(f"page_{page_id}.png")
    api_headers = {"X-API-Key": API_KEY}
    files = {"images": (f"page_{page_id}.png", open(f"page_{page_id}.png", "rb"), "image/png")}
    data = {"dither": "true", "pageId": str(page_id)}
    requests.post(PUSH_URL, headers=api_headers, files=files, data=data)

# ================= 页面 1 & 2：知乎热榜 (保持动态高度) =================
# ... 此处省略 task_zhihu 代码，保持和你之前运行的版本一致 ...

# ================= 页面 3：全屏实体台历样式 (阳历+农历) =================

def task_full_calendar():
    print("生成全屏台历页面...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)
    
    now = datetime.now()
    year, month, today = now.year, now.month, now.day
    month_en = now.strftime("%B")

    # 1. 顶部表头：大数字月份 + 年份 + 英文月份
    draw.text((20, 10), str(month), font=font_large, fill=0)
    draw.text((80, 20), month_en, font=font_title, fill=0)
    draw.text((80, 45), str(year), font=font_item, fill=0)
    draw.line([(20, 75), (380, 75)], fill=0, width=2)

    # 2. 星期表头 (日 一 二 三 四 五 六)
    week_headers = ["日", "一", "二", "三", "四", "五", "六"]
    col_width = 52
    for i, header in enumerate(week_headers):
        draw.text((25 + i * col_width, 85), header, font=font_small, fill=0)

    # 3. 日历网格
    # 设置周日为一周的第一天
    calendar.setfirstweekday(calendar.SUNDAY)
    cal = calendar.monthcalendar(year, month)
    
    start_y = 110
    row_height = 38
    
    for r, week in enumerate(cal):
        for c, day in enumerate(week):
            if day != 0:
                dx = 25 + c * col_width
                dy = start_y + r * row_height
                
                # 如果是今天，画一个圆圈或方框
                if day == today:
                    draw.rounded_rectangle([(dx-5, dy-2), (dx+35, dy+32)], radius=5, outline=0, width=1)
                
                # 阳历数字
                draw.text((dx, dy), str(day), font=font_item, fill=0)
                
                # 农历日期或节日
                lunar_txt = get_lunar_text(year, month, day)
                # 如果是节日，加粗或者稍微下移
                draw.text((dx, dy + 18), lunar_txt, font=font_tiny, fill=0)

    push_image(img, 3)

# ================= 页面 4：综合看板 (天大北洋园专属) =================

def task_dashboard():
    print("生成看板页面...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)
    
    # 尝试获取津南区天气
    try:
        url = f"http://t.weather.itboy.net/api/weather/city/{WEATHER_CITY_CODE}"
        weather_data = requests.get(url, timeout=10).json()
        data = weather_data['data']['forecast'][0]
        # 修正显示名称
        wea_str = f"天大北洋园 | {data['type']}"
        temp_str = f"{data['low'].replace('低温 ','')}~{data['high'].replace('高温 ','')}"
        tip = data['notice']
    except:
        wea_str, temp_str, tip = "津南区 | 未知", "0~0℃", "获取失败"

    # 左侧：天气方块
    draw.rounded_rectangle([(10, 10), (195, 120)], radius=10, fill=0)
    draw.text((20, 20), wea_str, font=font_title, fill=255) # 字体大一点会由于字符多显示不下，已微调
    draw.text((20, 60), temp_str, font=font_title, fill=255)
    
    # 右侧：倒计时
    days_to_weekend = 5 - datetime.today().weekday()
    draw.rounded_rectangle([(205, 10), (390, 120)], radius=10, fill=0)
    draw.text((215, 20), "距离周末", font=font_item, fill=255)
    draw.text((215, 60), "已是周末!" if days_to_weekend <= 0 else f"还有 {days_to_weekend} 天", font=font_title, fill=255)

    # 穿衣建议
    draw.text((10, 135), "👕 建议:", font=font_item, fill=0)
    # 简单的手动换行逻辑
    tip_lines = [tip[i:i+19] for i in range(0, len(tip), 19)]
    for i, line in enumerate(tip_lines[:2]):
        draw.text((10, 160 + i*22), line, font=font_item, fill=0)

    # 每日一言
    try:
        hito = requests.get("https://v1.hitokoto.cn/?c=i", timeout=5).json()['hitokoto']
    except:
        hito = "实事求是。" # 天大校训作为兜底
        
    draw.line([(10, 220), (390, 220)], fill=0, width=2)
    draw.text((10, 230), "「每日一言」", font=font_small, fill=0)
    hito_lines = [hito[i:i+20] for i in range(0, len(hito), 20)]
    for i, line in enumerate(hito_lines[:2]):
        draw.text((10, 250 + i*25), line, font=font_item, fill=0)

    push_image(img, 4)

# ================= 执行 =================

if __name__ == "__main__":
    # task_zhihu()     # 如果需要知乎可以开启
    task_full_calendar() # 页面 3：实体台历风格
    task_dashboard()     # 页面 4：天大北洋园天气
    print("执行完毕！")
