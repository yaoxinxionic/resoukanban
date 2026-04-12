import os
import requests
import calendar
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
from zhdate import ZhDate

# ================= 配置区 =================
API_KEY = os.environ.get("ZECTRIX_API_KEY")
MAC_ADDRESS = os.environ.get("ZECTRIX_MAC")
PUSH_URL = f"https://cloud.zectrix.com/open/v1/devices/{MAC_ADDRESS}/display/image"

# 和风天气配置（需要注册获取免费key：https://dev.qweather.com）
QWEATHER_KEY = os.environ.get("QWEATHER_API_KEY")  # 请设置环境变量，或直接填字符串
CITY_CODE = "101030103"  # 津南区

FONT_PATH = "font.ttf"
try:
    font_huge = ImageFont.truetype(FONT_PATH, 55)   # 月份大数字
    font_title = ImageFont.truetype(FONT_PATH, 24)  # 标题
    font_item = ImageFont.truetype(FONT_PATH, 18)   # 阳历/建议
    font_tiny = ImageFont.truetype(FONT_PATH, 11)   # 农历/节气
    font_small = ImageFont.truetype(FONT_PATH, 14)  # 星期
except:
    print("错误: 找不到 font.ttf")
    exit(1)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# ================= 节气近似判断（无需额外库）=================
def get_solar_term(year, month, day):
    """根据日期返回节气名称（仅主要节气），无节气返回None"""
    # 数据格式: (月, 日范围, 名称)
    terms = [
        (2, (3,5), "立春"), (2, (18,20), "雨水"),
        (3, (5,7), "惊蛰"), (3, (20,22), "春分"),
        (4, (4,6), "清明"), (4, (19,21), "谷雨"),
        (5, (5,7), "立夏"), (5, (20,22), "小满"),
        (6, (5,7), "芒种"), (6, (21,22), "夏至"),
        (7, (6,8), "小暑"), (7, (22,24), "大暑"),
        (8, (7,9), "立秋"), (8, (22,24), "处暑"),
        (9, (7,9), "白露"), (9, (22,24), "秋分"),
        (10, (8,9), "寒露"), (10, (23,24), "霜降"),
        (11, (7,8), "立冬"), (11, (22,23), "小雪"),
        (12, (6,8), "大雪"), (12, (21,23), "冬至"),
        (1, (5,7), "小寒"), (1, (20,22), "大寒")
    ]
    for m, (d_low, d_high), name in terms:
        if month == m and d_low <= day <= d_high:
            return name
    return None

def get_lunar_or_term(y, m, d):
    """返回应在日期下方显示的文字（节气/节日优先，否则农历）"""
    try:
        # 1. 节气（如清明、谷雨）
        term = get_solar_term(y, m, d)
        if term:
            return term

        # 2. 法定节日
        fests = {(1,1):"元旦", (5,1):"劳动节", (10,1):"国庆节"}
        if (m, d) in fests:
            return fests[(m, d)]

        # 3. 农历节日（春节、端午、中秋）
        date_obj = datetime(y, m, d)
        lunar = ZhDate.from_datetime(date_obj)
        l_fests = {(1,1):"春节", (5,5):"端午", (8,15):"中秋"}
        if (lunar.lunar_month, lunar.lunar_day) in l_fests:
            return l_fests[(lunar.lunar_month, lunar.lunar_day)]

        # 4. 普通农历日期（如“初八”）
        return lunar.lunar_date_str()[-2:]  # 取后两位
    except:
        return ""   # 显示不了就留空

# ================= 和风天气获取（含逐小时温度）=================
def get_qweather():
    """返回 (城市名, 天气现象, 最低温, 最高温, 小时温度列表) 或 None"""
    if not QWEATHER_KEY:
        print("警告: 未设置 QWEATHER_API_KEY，天气功能不可用")
        return None
    try:
        # 3天预报（获取今日高低温和天气现象）
        url_3d = f"https://devapi.qweather.com/v7/weather/3d?location={CITY_CODE}&key={QWEATHER_KEY}"
        resp_3d = requests.get(url_3d, timeout=10).json()
        if resp_3d.get('code') != '200':
            raise Exception("3d接口返回错误")
        today = resp_3d['daily'][0]
        city_name = "津南区"
        weather_text = today['textDay']
        temp_min = today['tempMin']
        temp_max = today['tempMax']

        # 24小时预报（获取逐小时温度）
        url_24h = f"https://devapi.qweather.com/v7/weather/24h?location={CITY_CODE}&key={QWEATHER_KEY}"
        resp_24h = requests.get(url_24h, timeout=10).json()
        if resp_24h.get('code') != '200':
            raise Exception("24h接口返回错误")
        hourly = resp_24h['hourly']
        # 提取温度和时间（只取未来12小时，避免曲线太密）
        hours = []
        temps = []
        now_hour = datetime.now().hour
        for item in hourly[:12]:  # 未来12小时
            fx_time = datetime.fromisoformat(item['fxTime'])
            hour = fx_time.hour
            temp = int(item['temp'])
            hours.append(hour)
            temps.append(temp)
        return city_name, weather_text, temp_min, temp_max, (hours, temps)
    except Exception as e:
        print(f"和风天气获取失败: {e}")
        return None

def draw_temp_curve(draw, hours, temps, x0, y0, width, height):
    """绘制温度折线图，并标注首尾温度"""
    if len(temps) < 2:
        draw.text((x0, y0), "温度数据不足", font=font_item, fill=0)
        return
    # 坐标映射
    x_step = width / (len(hours)-1)
    y_min, y_max = min(temps), max(temps)
    y_range = y_max - y_min if y_max != y_min else 1
    points = []
    for i, (h, t) in enumerate(zip(hours, temps)):
        x = x0 + i * x_step
        y = y0 + height - (t - y_min) / y_range * height
        points.append((x, y))
    # 画折线
    draw.line(points, fill=0, width=2)
    # 标注起点和终点温度
    draw.text((x0, y0-12), f"{temps[0]}℃", font=font_tiny, fill=0)
    draw.text((x0+width-20, y0-12), f"{temps[-1]}℃", font=font_tiny, fill=0)
    # 可选：标注几个关键时间点（每隔3小时）
    for i in range(0, len(hours), 3):
        x = x0 + i * x_step
        draw.text((x-8, y0+height+2), f"{hours[i]}时", font=font_tiny, fill=0)

# ================= 推送图片 =================
def push_image(img, page_id):
    img.save(f"page_{page_id}.png")
    api_headers = {"X-API-Key": API_KEY}
    files = {"images": (f"page_{page_id}.png", open(f"page_{page_id}.png", "rb"), "image/png")}
    data = {"dither": "true", "pageId": str(page_id)}
    requests.post(PUSH_URL, headers=api_headers, files=files, data=data)

# ================= Page 3: 实体台历 =================
def task_calendar():
    print("生成 Page 3: 实体台历...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)

    now = datetime.now()
    y, m, today = now.year, now.month, now.day

    # 顶部排版
    draw.text((20, 10), str(m), font=font_huge, fill=0)
    draw.text((85, 20), now.strftime("%B"), font=font_title, fill=0)
    draw.text((85, 48), str(y), font=font_item, fill=0)
    draw.line([(20, 78), (380, 78)], fill=0, width=2)

    # 星期头
    headers = ["日", "一", "二", "三", "四", "五", "六"]
    col_w = 53
    for i, h in enumerate(headers):
        draw.text((25 + i*col_w, 88), h, font=font_small, fill=0)

    # 绘制日历
    calendar.setfirstweekday(calendar.SUNDAY)
    cal = calendar.monthcalendar(y, m)
    curr_y = 115
    row_h = 38

    for week in cal:
        for c, day in enumerate(week):
            if day != 0:
                dx = 25 + c * col_w
                # 今日边框
                if day == today:
                    draw.rounded_rectangle([(dx-3, curr_y-2), (dx+36, curr_y+32)], radius=5, outline=0)

                # 阳历数字（始终显示）
                draw.text((dx+2, curr_y), str(day), font=font_item, fill=0)

                # 下方文字：节气/节日 > 农历（若获取不到则不显示）
                bottom_text = get_lunar_or_term(y, m, day)
                if bottom_text:
                    # 若文字长度超过3个汉字，缩小字体或压缩显示
                    if len(bottom_text) > 3:
                        try:
                            font_smaller = ImageFont.truetype(FONT_PATH, 10)
                            draw.text((dx+2, curr_y+18), bottom_text, font=font_smaller, fill=0)
                        except:
                            draw.text((dx+2, curr_y+18), bottom_text[:3], font=font_tiny, fill=0)
                    else:
                        draw.text((dx+2, curr_y+18), bottom_text, font=font_tiny, fill=0)
        curr_y += row_h

    push_image(img, 3)

# ================= Page 4: 综合看板（和风天气+温度曲线）=================
def task_dashboard():
    print("生成 Page 4: 综合看板 (和风天气 + 逐小时曲线)...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)

    # 获取和风天气数据
    weather = get_qweather()
    if weather:
        city_name, weather_text, temp_min, temp_max, (hours, temps) = weather
        title_str = f"{city_name} | {weather_text}"
        temp_range = f"{temp_min}℃ ~ {temp_max}℃"
    else:
        title_str = "津南区 | 天气获取失败"
        temp_range = "请检查API Key"
        hours, temps = [], []  # 无曲线数据

    # 1. 左侧深色模块（天气）
    draw.rounded_rectangle([(10, 10), (195, 120)], radius=10, fill=0)
    draw.text((20, 20), title_str, font=font_title, fill=255)
    draw.text((20, 60), temp_range, font=font_title, fill=255)

    # 2. 右侧深色模块（周末倒计时）
    days = 5 - datetime.today().weekday()
    draw.rounded_rectangle([(205, 10), (390, 120)], radius=10, fill=0)
    draw.text((215, 20), "距离周末", font=font_item, fill=255)
    draw.text((215, 60), "已是周末!" if days <= 0 else f"还有 {days} 天", font=font_title, fill=255)

    # 3. 逐小时温度曲线（替换原穿衣建议区域）
    if hours and temps:
        draw.text((10, 135), "📈 逐小时温度曲线", font=font_item, fill=0)
        # 曲线绘图区域：x0=10, y0=155, width=380, height=55
        draw_temp_curve(draw, hours, temps, 10, 155, 380, 55)
    else:
        draw.text((10, 135), "📈 逐小时温度曲线 (数据不可用)", font=font_item, fill=0)

    # 4. 每日一言（向下移动至 y=240 附近）
    try:
        hito = requests.get("https://v1.hitokoto.cn/?c=i", timeout=5).json()['hitokoto']
    except:
        hito = "实事求是。"
    draw.line([(10, 225), (390, 225)], fill=0, width=2)   # 分割线上移
    draw.text((10, 235), "「每日一言」", font=font_small, fill=0)
    # 自动换行（每行20字）
    hito_lines = [hito[i:i+20] for i in range(0, len(hito), 20)]
    for i, line in enumerate(hito_lines[:2]):
        draw.text((10, 255 + i*25), line, font=font_item, fill=0)

    push_image(img, 4)

if __name__ == "__main__":
    task_calendar()
    task_dashboard()
    print("全部执行完毕！")
