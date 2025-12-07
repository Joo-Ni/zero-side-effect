import os
import pymysql
from backend.config import settings

# 제품명 기반 썸네일

conn = pymysql.connect(
    host=settings.DB_HOST,
    user=settings.DB_USER,
    password=settings.DB_PASSWORD,
    database=settings.DB_NAME,
    charset="utf8mb4"
)

cur = conn.cursor()

folder = "backend/static/thumbnails"
exts = [".png", ".jpg", ".jpeg", ".webp"]

cur.execute("select id, name from products")
rows = cur.fetchall()

ok = 0
miss = []

for pid, name in rows:
    img = None

    for e in exts:
        f = name + e
        path = os.path.join(folder, f)
        if os.path.exists(path):
            img = "/static/thumbnails/" + f
            break

    if img:
        cur.execute("update products set image_url=%s where id=%s", (img, pid))
        ok += 1
    else:
        miss.append(name)

conn.commit()
cur.close()
conn.close()

print("updated:", ok)
print("missing:", miss)
