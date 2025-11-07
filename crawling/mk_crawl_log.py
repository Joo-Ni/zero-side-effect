import csv

headers = ["product_name", "category", "image_count", "timestamp", "directory"]
row = {
    "product_name": "립톤제로복숭아 아이스티",
    "category": "음료",
    "image_count": "",
    "timestamp": "",
    "directory": "",
}

with open("crawl_log.csv", "w", newline="", encoding="cp949") as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    writer.writerow(row)

print("crawl_log.csv created.")