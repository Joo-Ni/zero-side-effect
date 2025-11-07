import csv
import os
import time
from datetime import datetime
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from PIL import Image
from io import BytesIO

CSV_FILE = "crawl_log.csv"
BASE_SAVE_DIR = "dataset_naver"

def get_save_path(category, product_name):
    folder_name = product_name.replace(" ", "_")
    save_path = os.path.join(BASE_SAVE_DIR, category, folder_name)
    os.makedirs(save_path, exist_ok=True)
    return save_path

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920x1080")
    return webdriver.Chrome(options=options)

def scroll_to_load(driver, scroll_pause=1, max_scrolls=15):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for i in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("⛔ 스크롤 종료 (더 이상 로딩되지 않음)")
            break
        last_height = new_height
        print(f"🔽 스크롤 {i+1}/{max_scrolls} 완료")

def crawl_naver_images(product_name, category, max_images=300):
    save_path = get_save_path(category, product_name)
    driver = setup_driver()
    search_url = f"https://search.naver.com/search.naver?where=image&query={product_name}"
    driver.get(search_url)
    time.sleep(2)
    scroll_to_load(driver)

    img_elements = driver.find_elements(By.CSS_SELECTOR, "img._fe_image_tab_content_thumbnail_image")
    print(f"🔍 {product_name} 에서 이미지 {len(img_elements)}개 감지됨")

    count = 0
    for idx, img in enumerate(img_elements):
        if count >= max_images:
            break
        src = img.get_attribute("src")
        if src and src.startswith("http"):
            try:
                response = requests.get(src, timeout=3)
                image = Image.open(BytesIO(response.content))
                ext = image.format.lower()
                filename = os.path.join(save_path, f"{count+1:03d}.{ext}")
                image.save(filename)
                print(f"✅ [{count+1}] 저장 완료: {filename}")
                count += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"❌ 이미지 저장 실패: {e}")

    driver.quit()
    print(f"🎉 {product_name} → 최종 {count}개 저장 완료 at {save_path}")
    return count, save_path.replace("\\", "/")

def update_csv(product_name, category, image_count, save_path):
    df = pd.read_csv(CSV_FILE, encoding="cp949")
    for i, row in df.iterrows():
        if row["product_name"] == product_name and row["category"] == category:
            df.at[i, "image_count"] = image_count
            df.at[i, "timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            df.at[i, "directory"] = save_path
    df.to_csv(CSV_FILE, index=False, encoding="cp949")

if __name__ == "__main__":
    df = pd.read_csv(CSV_FILE, encoding="cp949")
    for _, row in df.iterrows():
        name = row["product_name"]
        category = row["category"]
        if pd.isna(row["image_count"]) or pd.isna(row["timestamp"]):
            print(f"\n🚀 크롤링 시작: [{category}] {name}")
            count, path = crawl_naver_images(name, category)
            update_csv(name, category, count, path)
        else:
            print(f"⏩ 이미 크롤링 완료된 제품 스킵: [{category}] {name}")
