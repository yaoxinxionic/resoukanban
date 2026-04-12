import os
import requests
import calendar
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta  # 新增 timedelta
from zhdate import ZhDate

# ================= 配置区 =================
API_KEY = os.environ.get("ZECTRIX_API_KEY")
MAC_ADDRESS = os.environ.get("ZECTRIX_MAC")
PUSH_URL = f"https://cloud.zectrix.com/open/v1/devices/{MAC_ADDRESS}/display/image"

FONT_PATH = "font.ttf"
try:
    font_huge = ImageFont.truetype(FONT_PATH, 65)   # 月份大字/实时气温
    font_title = ImageFont.truetype(FONT_PATH, 24)  # 标题栏
    font_item = ImageFont.truetype(FONT_PATH, 18)   # 正文/阳历/建议/未来天气
    font_small = ImageFont.truetype(FONT_PATH, 14)  # 序号/星期/辅助信息
    font_tiny = ImageFont.truetype(FONT_PATH, 11)   # 农历/细节
    font_48 = ImageFont.truetype(FONT_PATH, 48)     # 当前温度专用
    font_36 = ImageFont.truetype(FONT_PATH, 36)     # 天气描述专用
except:
    print("错误: 找不到 font.ttf，请确保字体文件在同一目录下")
    exit(1)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# ================= 工具函数 =================
def get_wrapped_lines(text, max_chars=18):
    lines = []
    while text:
        lines.append(text[:max_chars])
        text = text[max_chars:]
    return lines

def get_clothing_advice(temp):
    try:
        t = int(temp)
        if t >= 28: return "建议穿短袖、短裤，注意防晒补水。"
        elif t >= 22: return "体感舒适，建议穿 T 恤配薄长裤。"
        elif t >= 16: return "建议穿长袖衬衫、卫衣或单层薄外套。"
        elif t >= 10: return "气温微凉，建议穿夹克、风衣或毛衣。"
        elif t >= 5: return "建议穿大衣、厚毛衣或薄款羽绒服。"
        else: return "天气寒冷，建议穿厚羽绒服，注意防寒。"
    except:
        return "请根据实际体感气温调整着装。"

# ================= 精确节气与农历节日 =================
def get_solar_term(year, month, day):
    term_table = {
        (2024,2,4):"立春", (2024,2,19):"雨水", (2024,3,5):"惊蛰", (2024,3,20):"春分",
        (2024,4,4):"清明", (2024,4,19):"谷雨", (2024,5,5):"立夏", (2024,5,20):"小满",
        (2024,6,5):"芒种", (2024,6,21):"夏至", (2024,7,6):"小暑", (2024,7,22):"大暑",
        (2024,8,7):"立秋", (2024,8,22):"处暑", (2024,9,7):"白露", (2024,9,22):"秋分",
        (2024,10,8):"寒露", (2024,10,23):"霜降", (2024,11,7):"立冬", (2024,11,22):"小雪",
        (2024,12,6):"大雪", (2024,12,21):"冬至",
        (2025,1,5):"小寒", (2025,1,20):"大寒", (2025,2,3):"立春", (2025,2,18):"雨水",
        (2025,3,5):"惊蛰", (2025,3,20):"春分", (2025,4,4):"清明", (2025,4,20):"谷雨",
        (2025,5,5):"立夏", (2025,5,21):"小满", (2025,6,5):"芒种", (2025,6,21):"夏至",
        (2025,7,7):"小暑", (2025,7,22):"大暑", (2025,8,7):"立秋", (2025,8,23):"处暑",
        (2025,9,7):"白露", (2025,9,22):"秋分", (2025,10,8):"寒露", (2025,10,23):"霜降",
        (2025,11,7):"立冬", (2025,11,22):"小雪", (2025,12,7):"大雪", (2025,12,21):"冬至",
        (2026,1,5):"小寒", (2026,1,20):"大寒", (2026,2,4):"立春", (2026,2,18):"雨水",
        (2026,3,5):"惊蛰", (2026,3,20):"春分", (2026,4,5):"清明", (2026,4,20):"谷雨",
        (2026,5,5):"立夏", (2026,5,21):"小满", (2026,6,6):"芒种", (2026,6,21):"夏至",
        (2026,7,7):"小暑", (2026,7,23):"大暑", (2026,8,7):"立秋", (2026,8,23):"处暑",
        (2026,9,7):"白露", (2026,9,23):"秋分", (2026,10,8):"寒露", (2026,10,23):"霜降",
        (2026,11,7):"立冬", (2026,11,22):"小雪", (2026,12,7):"大雪", (2026,12,21):"冬至",
        (2027,1,5):"小寒", (2027,1,20):"大寒", (2027,2,4):"立春", (2027,2,19):"雨水",
        (2027,3,6):"惊蛰", (2027,3,21):"春分", (2027,4,5):"清明", (2027,4,20):"谷雨",
    }
    return term_table.get((year, month, day), None)

def get_lunar_or_festival(y, m, d):
    term = get_solar_term(y, m, d)
    if term:
        return term
    solar_fests = {
        (1,1):"元旦", (2,14):"情人节", (3,8):"妇女节", (4,1):"愚人节",
        (5,1):"劳动节", (6,1):"儿童节", (7,1):"建党节", (8,1):"建军节",
        (9,10):"教师节", (10,1):"国庆节", (12,25):"圣诞节"
    }
    if (m, d) in solar_fests:
        return solar_fests[(m, d)]
    try:
        lunar = ZhDate.from_datetime(datetime(y, m, d))
        lm, ld = lunar.lunar_month, lunar.lunar_day
        lunar_fests = {
            (1,1):"春节", (1,15):"元宵节", (5,5):"端午节",
            (7,7):"七夕节", (8,15):"中秋节", (9,9):"重阳节", (12,30):"除夕"
        }
        if (lm, ld) in lunar_fests:
            return lunar_fests[(lm, ld)]
        days = ["初一","初二","初三","初四","初五","初六","初七","初八","初九","初十",
                "十一","十二","十三","十四","十五","十六","十七","十八","十九","二十",
                "廿一","廿二","廿三","廿四","廿五","廿六","廿七","廿八","廿九","三十"]
        months = ["正月","二月","三月","四月","五月","六月","七月","八月","九月","十月","冬月","腊月"]
        if ld == 1:
            return months[lm-1]
        return days[ld-1]
    except:
        return ""

def push_image(img, page_id):
    img.save(f"page_{page_id}.png")
    api_headers = {"X-API-Key": API_KEY}
    files = {"images": (f"page_{page_id}.png", open(f"page_{page_id}.png", "rb"), "image/png")}
    data = {"dither": "true", "pageId": str(page_id)}
    try:
        res = requests.post(PUSH_URL, headers=api_headers, files=files, data=data)
        print(f"Page {page_id} 推送成功: {res.status_code}")
    except Exception as e:
        print(f"Page {page_id} 推送失败: {e}")

# ================= 页面 1 & 2: 知乎热榜 =================
def task_zhihu():
    print("获取知乎热榜...")
    try:
        url = "https://api.zhihu.com/topstory/hot-list"
        res = requests.get(url, headers=HEADERS, timeout=10).json()
        titles = [item['target']['title'] for item in res['data']]
    except Exception as e:
        print(f"知乎获取异常: {e}")
        titles = ["数据获取失败，请检查网络"] * 10

    def draw_list(draw, page_title, items, start_idx):
        draw.rounded_rectangle([(10, 10), (390, 45)], radius=8, fill=0)
        draw.text((20, 15), page_title, font=font_title, fill=255)
        y, last_idx = 55, start_idx
        item_gap = 12
        line_height = 22
        for i in range(start_idx, len(items)):
            lines = get_wrapped_lines(items[i], 19)
            required_h = len(lines) * line_height
            if y + required_h > 295:
                break
            current_num = i + 1
            draw.rounded_rectangle([(10, y), (36, y+24)], radius=6, fill=0)
            num_x = 18 if current_num < 10 else 11
            draw.text((num_x, y+2), str(current_num), font=font_small, fill=255)
            curr_y = y + 2
            for line in lines:
                draw.text((45, curr_y), line, font=font_item, fill=0)
                curr_y += line_height
            y += max(24, required_h) + item_gap
            last_idx = i + 1
            if y < 290:
                draw.line([(45, y - item_gap/2), (380, y - item_gap/2)], fill=0, width=1)
        return last_idx

    img1 = Image.new('1', (400, 300), color=255)
    next_s = draw_list(ImageDraw.Draw(img1), "◆ 知乎热榜 (一)", titles, 0)
    push_image(img1, 1)

    img2 = Image.new('1', (400, 300), color=255)
    draw_list(ImageDraw.Draw(img2), "◆ 知乎热榜 (二)", titles, next_s)
    push_image(img2, 2)

# ================= 页面 3: 日历 =================
def task_calendar():
    print("生成 Page 3: 实体台历...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)

    now = datetime.now()
    y, m, today = now.year, now.month, now.day

    draw.text((20, 10), str(m), font=font_huge, fill=0)
    draw.text((90, 20), now.strftime("%B"), font=font_title, fill=0)
    draw.text((90, 48), str(y), font=font_item, fill=0)
    draw.line([(20, 78), (380, 78)], fill=0, width=2)

    headers = ["日", "一", "二", "三", "四", "五", "六"]
    col_w = 53
    for i, h in enumerate(headers):
        draw.text((25 + i*col_w, 88), h, font=font_small, fill=0)

    calendar.setfirstweekday(calendar.SUNDAY)
    cal = calendar.monthcalendar(y, m)
    curr_y, row_h = 115, 38

    for week in cal:
        for c, day in enumerate(week):
            if day != 0:
                dx = 25 + c * col_w
                if day == today:
                    draw.rounded_rectangle([(dx-3, curr_y-2), (dx+35, curr_y+32)], radius=5, outline=0)
                draw.text((dx+2, curr_y), str(day), font=font_item, fill=0)
                bottom_text = get_lunar_or_festival(y, m, day)
                if bottom_text:
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

# ================= 风速转换 =================
def kmph_to_wind_scale(kmph):
    if kmph < 1: return 0
    elif kmph <= 5: return 1
    elif kmph <= 11: return 2
    elif kmph <= 19: return 3
    elif kmph <= 28: return 4
    elif kmph <= 38: return 5
    elif kmph <= 49: return 6
    elif kmph <= 61: return 7
    elif kmph <= 74: return 8
    elif kmph <= 88: return 9
    elif kmph <= 102: return 10
    elif kmph <= 117: return 11
    else: return 12

# ================= 页面 4: 天气看板（带更新时间，右侧卡片下移） =================
def task_weather_dashboard():
    print("生成 Page 4: 气象仪表盘 (津南)...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)

    def draw_bold_text(draw, xy, text, font, fill=0, offset=1):
        """通过两次绘制（水平偏移1像素）模拟加粗"""
        x, y = xy
        draw.text((x, y), text, font=font, fill=fill)
        draw.text((x + offset, y), text, font=font, fill=fill)

    try:
        url = "https://wttr.in/Jinnan,Tianjin?format=j1&lang=zh"
        resp = requests.get(url, timeout=15).json()
        curr = resp['current_condition'][0]
        curr_temp = int(curr['temp_C'])
        weather_text = curr['lang_zh'][0]['value']
        humidity = curr['humidity']
        wind_kmph = int(curr['windspeedKmph'])
        wind_scale = kmph_to_wind_scale(wind_kmph)
        uv_index = curr.get('uvIndex', 'N/A')
        astro = resp['weather'][0]['astronomy'][0]
        sunrise = astro['sunrise']
        sunset = astro['sunset']
        
        today_weather = resp['weather'][0]
        today_high = today_weather['maxtempC']
        today_low = today_weather['mintempC']
        
        forecasts = resp['weather'][1:3]
        
        now_utc = datetime.utcnow()
        now_beijing = now_utc + timedelta(hours=8)
        update_time = now_beijing.strftime("%H:%M")
        
        draw.text((20, 10), "津南区 | 天大北洋园", font=font_title, fill=0)
        time_text = f"更新: {update_time}"
        try:
            bbox = draw.textbbox((0, 0), time_text, font=font_small)
            time_width = bbox[2] - bbox[0]
        except:
            time_width = len(time_text) * 8
        draw.text((390 - time_width, 12), time_text, font=font_small, fill=0)

        draw.text((25, 40), f"{curr_temp}°C", font=font_48, fill=0)
        # 今日高低温度加粗
        draw_bold_text(draw, (25, 100), f"{today_low}°/{today_high}°", font=font_item)
        draw.text((150, 45), f"{weather_text}", font=font_36, fill=0)

        draw.rounded_rectangle([(235, 45), (385, 130)], radius=8, outline=0, fill=0)
        draw.text((245, 55), f"[湿] {humidity}%", font=font_small, fill=255)
        draw.text((245, 80), f"[风] {wind_scale}级", font=font_small, fill=255)
        draw.text((245, 105), f"☀️ 紫外线 {uv_index}", font=font_small, fill=255)

        draw_bold_text(draw, (25, 135), f"日出 {sunrise}   日落 {sunset}", font=font_item)

        draw.line([(20, 160), (380, 160)], fill=0, width=1)
        x_positions = [30, 200]
        for i, day in enumerate(forecasts):
            x = x_positions[i]
            date_str = day['date'][5:]
            high = day['maxtempC']
            low = day['mintempC']
            weather_desc = day['hourly'][4]['lang_zh'][0]['value']
            draw_bold_text(draw, (x, 175), date_str, font=font_item)
            draw_bold_text(draw, (x, 200), weather_desc, font=font_item)
            draw_bold_text(draw, (x, 220), f"{low}°~{high}°", font=font_item)

        advice = get_clothing_advice(curr_temp)
        draw.line([(20, 250), (380, 250)], fill=0, width=1)
        advice_lines = [advice[i:i+18] for i in range(0, len(advice), 18)]
        for i, line in enumerate(advice_lines[:2]):
            draw_bold_text(draw, (20, 262 + i*24), f"[衣] {line}", font=font_item)

    except Exception as e:
        print(f"天气获取异常: {e}")
        draw.text((20, 50), "天气数据获取失败，请检查网络", font=font_item, fill=0)

    push_image(img, 4)
# ================= 主程序 =================
if __name__ == "__main__":
    if not API_KEY or not MAC_ADDRESS:
        print("错误: 请在 GitHub Secrets 中配置 ZECTRIX_API_KEY 和 ZECTRIX_MAC")
        exit(1)

    task_zhihu()
    task_calendar()
    task_weather_dashboard()
    print("所有任务执行完毕！")
