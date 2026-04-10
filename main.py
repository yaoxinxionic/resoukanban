import requests
from PIL import Image, ImageDraw, ImageFont
import os

# 1. 准备你的极趣设备信息（从你的截图里提取的）
API_KEY = "zt_3e0e73b124fdfab91690c73eeb1e529d"
MAC_ADDRESS = "20:6E:F1:B4:81:A8"
PUSH_URL = f"https://cloud.zectrix.com/open/v1/devices/{MAC_ADDRESS}/display/image"

def main():
    print("开始获取B站热搜...")
    # 2. 获取 B站 官方的免费热搜数据
    bilibili_url = "https://api.bilibili.com/x/web-interface/search/square?limit=10"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(bilibili_url, headers=headers).json()
    trending_list = response['data']['trending']['list']
    
    # 3. 准备画图（创建 400x300 的白色图片）
    print("正在生成图片...")
    img = Image.new('1', (400, 300), color=255) # 255是白色
    draw = ImageDraw.Draw(img)
    
    # 下载一个免费的黑体中文字体（防止云端电脑没有中文字体显示乱码）
    font_path = "kaiti.ttf"  # 直接读取你刚才上传的楷体文件
    
    # 设置字体大小（标题稍微大点，内容小点）
    font_title = ImageFont.truetype(font_path, 26)
    font_content = ImageFont.truetype(font_path, 18)
    
    # 在图片上写字
    draw.text((10, 10), "🔥 B站实时热搜榜", font=font_title, fill=0) # 0是黑色
    
    y_position = 55
    for i, item in enumerate(trending_list[:9]): # 取前9条，多了放不下
        keyword = item['keyword']
        # 画一条热搜，比如 "1. 某某事件"
        draw.text((10, y_position), f"{i+1}. {keyword}", font=font_content, fill=0)
        y_position += 26 # 每写一行，往下挪26个像素
        
    img.save("hot.png")
    
    # 4. 把画好的图片推送给极趣墨水屏
    print("正在推送到墨水屏...")
    api_headers = {"X-API-Key": API_KEY}
    files = {"images": ("hot.png", open("hot.png", "rb"), "image/png")}
    data = {"dither": "true", "pageId": "2"} # 自动开启抖动算法，推送到第1页
    
    res = requests.post(PUSH_URL, headers=api_headers, files=files, data=data)
    print("极趣服务器返回结果:", res.text)

if __name__ == "__main__":
    main()
