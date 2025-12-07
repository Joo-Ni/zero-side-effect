# -*- coding: utf-8 -*-
# 썸네일 이미지를 기준으로 실제 데이터셋에서 비슷한 이미지만 골라내는 스크립트

import os
import csv
import shutil
from pathlib import Path
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications.efficientnet import EfficientNetB0, preprocess_input

CONFIG = {
    "dataset_root": "./dataset_naver",
    "thumbnail_dir": "./thumbnail",
    "out_accept_root": "./filtered_dataset",
    "threshold": 0.40,
    "image_size": 224,
    "batch_size": 64,
    "exts": [".jpg", ".jpeg", ".png", ".bmp", ".webp"],
    "log_csv": "./filter_log.csv"
}

# EfficientNet 임베딩 모델
class FeatureExtractor:
    def __init__(self, img_size):
        model = EfficientNetB0(include_top=False, weights="imagenet", pooling="avg")
        self.model = model
        self.img_size = img_size

    def load_img(self, path):
        raw = tf.io.read_file(str(path))
        img = tf.io.decode_image(raw, channels=3, expand_animations=False)
        img = tf.image.resize(img, [self.img_size, self.img_size])
        img = preprocess_input(tf.cast(img, tf.float32))
        return img.numpy()

    def extract_one(self, path):
        arr = self.load_img(path)
        return self.model.predict(arr[None, ...], verbose=0)[0]

    def extract_batch(self, paths, batch_size):
        imgs = []
        for p in paths:
            try:
                imgs.append(self.load_img(p))
            except:
                imgs.append(np.zeros((self.img_size, self.img_size, 3)))
        imgs = np.stack(imgs)
        return self.model.predict(imgs, batch_size=batch_size, verbose=0)

def cosine_similarity(a, b):
    a = a / (np.linalg.norm(a) + 1e-8)
    b = b / (np.linalg.norm(b) + 1e-8)
    return float(np.dot(a, b))

def main():
    ds_root = Path(CONFIG["dataset_root"])
    th_root = Path(CONFIG["thumbnail_dir"])
    out_root = Path(CONFIG["out_accept_root"])
    out_root.mkdir(parents=True, exist_ok=True)

    feat = FeatureExtractor(CONFIG["image_size"])

    th_files = sorted([p for p in th_root.iterdir() if p.suffix.lower() in CONFIG["exts"]])

    with open(CONFIG["log_csv"], "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["thumbnail", "category", "product", "kept", "total"])

        for th in th_files:
            th_vec = feat.extract_one(th)
            name = th.stem

            # 제품 폴더 매칭 (폴더명이 썸네일 이름과 비슷한 경우)
            matched = []
            for cat_dir in ds_root.iterdir():
                if not cat_dir.is_dir():
                    continue
                for prod_dir in cat_dir.iterdir():
                    if prod_dir.is_dir() and name in prod_dir.name:
                        matched.append(prod_dir)

            if not matched:
                writer.writerow([th.name, "", "", 0, 0])
                continue

            for prod in matched:
                imgs = [p for p in prod.iterdir() if p.suffix.lower() in CONFIG["exts"]]
                if not imgs:
                    writer.writerow([th.name, prod.parent.name, prod.name, 0, 0])
                    continue

                vecs = feat.extract_batch(imgs, CONFIG["batch_size"])
                keep = []
                for i, v in enumerate(vecs):
                    if cosine_similarity(th_vec, v) >= CONFIG["threshold"]:
                        keep.append(imgs[i])

                out_dir = out_root / prod.parent.name / prod.name
                out_dir.mkdir(parents=True, exist_ok=True)
                for img in keep:
                    shutil.copy2(img, out_dir / img.name)

                writer.writerow([th.name, prod.parent.name, prod.name, len(keep), len(imgs)])

if __name__ == "__main__":
    main()
