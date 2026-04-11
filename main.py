import os
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

# ================= 配置区 =================
API_KEY = os.environ.get("ZECTRIX_API_KEY")
MAC_ADDRESS = os.environ.get("ZECTRIX_MAC")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") # 新增：GitHub 免死金牌
PUSH_URL = f"https://cloud.zectrix.com/open/v1/devices/{MAC_ADDRESS}/display/image"

FONT_PATH = "font.ttf"
try:
    font_title = ImageFont.truetype(FONT_PATH, 24)
    font_item = ImageFont.truetype(FONT_PATH, 18)
    font_small = ImageFont.truetype(FONT_PATH, 14)
    font_large = ImageFont.truetype(FONT_PATH, 40)
except:
    print("错误: 找不到 font.ttf")
    exit(1)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# ================= 绘图辅助函数 =================
def draw_newsnow_style_list(draw, title, items):
    draw.rounded_rectangle([(10, 10), (390, 45)], radius=8, fill=0)
    draw.text((20, 15), title, font=font_title, fill=255)
    
    y = 55
    for i, text in enumerate(items[:8]): 
        box_w, box_h = 24, 24
        draw.rounded_rectangle([(10, y), (10+box_w, y+box_h)], radius=6, fill=0)
        draw.text((16 if i<9 else 12, y+2), str(i+1), font=font_small, fill=255)
        
        if len(text) > 19:
            text = text[:18] + "..."
        draw.text((45, y+2), text, font=font_item, fill=0)
        y += 30

def push_image(img, page_id):
    img.save("temp.png")
    api_headers = {"X-API-Key": API_KEY}
    files = {"images": ("temp.png", open("temp.png", "rb"), "image/png")}
    data = {"dither": "true", "pageId": str(page_id)}
    
    try:
        res = requests.post(PUSH_URL, headers=api_headers, files=files, data=data)
        print(f"推送第 {page_id} 页成功:", res.status_code)
    except Exception as e:
        print(f"推送第 {page_id} 页失败:", e)

# ================= 页面 1：知乎热榜 (极其稳定，不封海外IP) =================
def page1_zhihu():
    print("获取知乎热榜...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)
    
    items = []
    try:
        # 知乎官方的开源热榜接口，对 GitHub 非常友好
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        url = "https://api.zhihu.com/topstory/hot-list"
        res = requests.get(url, headers=headers, timeout=10).json()
        
        # 提取前 8 条热榜标题
        for item in res['data'][:8]:
            title = item['target']['title']
            items.append(title)
            
        if len(items) >= 5:
            print("知乎热榜获取成功！")
            
    except Exception as e:
        print("知乎获取报错:", e)
        items = ["获取数据失败，请检查网络..."] * 8
        
    draw_newsnow_style_list(draw, "🔥 知乎实时热榜", items)
    push_image(img, page_id=1)
# ================= 页面 2：GitHub 趋势 (免死金牌版) =================
def page2_github():
    print("获取 GitHub 趋势...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)
    
    items = []
    try:
        github_headers = HEADERS.copy()
        # 加上这把钥匙，GitHub 就知道你是内部自己人，不会再拦截你！
        if GITHUB_TOKEN:
            github_headers['Authorization'] = f"token {GITHUB_TOKEN}"
            
        last_week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        url = f"https://api.github.com/search/repositories?q=created:>{last_week}&sort=stars&order=desc"
        res = requests.get(url, headers=github_headers, timeout=10).json()
        for item in res['items'][:8]:
            items.append(f"{item['name']} ({item['stargazers_count']}★)")
    except Exception as e:
        print("GitHub获取报错:", e)
        items = ["获取数据失败..."] * 8
        
    draw_newsnow_style_list(draw, "💻 GitHub 热门开源", items)
    push_image(img, page_id=2)

# ================= 页面 3：综合看板 (稳定版) =================
def page3_dashboard():
    print("生成综合看板...")
    img = Image.new('1', (400, 300), color=255)
    draw = ImageDraw.Draw(img)
    
    try:
        url = "http://t.weather.itboy.net/api/weather/city/101030100"
        weather_data = requests.get(url, headers=HEADERS, timeout=10).json()
        city = weather_data['cityInfo']['city']
        forecast = weather_data['data']['forecast'][0]
        wea = forecast['type']
        high_str = forecast['high'].replace('高温 ', '')
        low_str = forecast['low'].replace('低温 ', '')
        
        h_temp = int(high_str.replace('℃', ''))
        l_temp = int(low_str.replace('℃', ''))
        avg_temp = (h_temp + l_temp) / 2
        
        if avg_temp >= 28: tip = "天气炎热，建议穿短袖、短裤、裙子等清凉衣物。"
        elif avg_temp >= 20: tip = "体感舒适，建议穿单层薄外套、长袖衬衫、T恤。"
        elif avg_temp >= 14: tip = "天气微凉，建议穿风衣、夹克、薄毛衣、休闲装。"
        elif avg_temp >= 5: tip = "天气较冷，建议穿秋裤、厚毛衣、外套或薄羽绒服。"
        else: tip = "天气寒冷，请穿厚羽绒服、保暖内衣，注意防寒！"
    except Exception as e:
        city, wea, high_str, low_str = "天津", "未知", "0℃", "0℃"
        tip = "获取天气失败，请注意关注当地气温变化。"

    draw.rounded_rectangle([(10, 10), (195, 120)], radius=10, fill=0)
    draw.text((20, 20), f"{city} | {wea}", font=font_title, fill=255)
    draw.text((20, 60), f"{low_str} ~ {high_str}", font=font_title, fill=255)
    
    today = datetime.today().weekday()
    days_to_weekend = 5 - today
    countdown_text = "已是周末!" if days_to_weekend <= 0 else f"还有 {days_to_weekend} 天"
        
    draw.rounded_rectangle([(205, 10), (390, 120)], radius=10, fill=0)
    draw.text((215, 20), "距离周末", font=font_item, fill=255)
    draw.text((215, 60), countdown_text, font=font_title, fill=255)

    draw.text((10, 135), "👕 建议:", font=font_item, fill=0)
    tip_line1 = tip[:18]
    tip_line2 = tip[18:36] + "..." if len(tip) > 36 else tip[18:]
    draw.text((10, 160), tip_line1, font=font_item, fill=0)
    draw.text((10, 185), tip_line2, font=font_item, fill=0)

    try:
        hitokoto = requests.get("https://v1.hitokoto.cn/?c=a", timeout=10).json()['hitokoto']
    except:
        hitokoto = "永远年轻，永远热泪盈眶。"
        
    draw.line([(10, 220), (390, 220)], fill=0, width=2)
    draw.text((10, 230), "「每日一言」", font=font_small, fill=0)
    
    hito_line1 = hitokoto[:20]
    hito_line2 = hitokoto[20:40] + "..." if len(hitokoto) > 40 else hitokoto[20:]
    draw.text((10, 250), hito_line1, font=font_item, fill=0)
    draw.text((10, 275), hito_line2, font=font_item, fill=0)

    push_image(img, page_id=3)

if __name__ == "__main__":
    if not API_KEY or not MAC_ADDRESS:
        print("错误: 请配置 GitHub Secrets")
        exit(1)
        
    page1_zhihu()
    page2_github()
    page3_dashboard()
    print("全部执行完毕！")
