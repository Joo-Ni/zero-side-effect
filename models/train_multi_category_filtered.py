# -*- coding: utf-8 -*-
# filtered_dataset 기준으로 카테고리별 EfficientNet 분류 모델을 학습하는 스크립트

import json
import random
from pathlib import Path
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.applications.efficientnet import EfficientNetB0, preprocess_input

CONFIG = {
    "root_dir": "./filtered_dataset",
    "models_root": "./models",
    "image_size": 224,
    "batch_size": 16,
    "epochs": 30,
    "val_split": 0.2,
    "lr": 1e-4,
    "seed": 42
}

EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

def load_dataset(cat_dir):
    files = []
    labels = []
    class_names = sorted([p.name for p in cat_dir.iterdir() if p.is_dir()])
    cls_to_idx = {n: i for i, n in enumerate(class_names)}

    for cls in class_names:
        p = cat_dir / cls
        imgs = [fp for fp in p.iterdir() if fp.suffix.lower() in EXTS]
        for img in imgs:
            files.append(str(img))
            labels.append(cls_to_idx[cls])

    return files, labels, class_names

def preprocess(path, label, img_size):
    img = tf.io.read_file(path)
    img = tf.io.decode_image(img, channels=3, expand_animations=False)
    img = tf.image.resize(img, [img_size, img_size])
    img = preprocess_input(tf.cast(img, tf.float32))
    return img, label

def build_model(num_classes, img_size):
    inputs = keras.Input((img_size, img_size, 3))
    aug = keras.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.05),
    ])
    x = aug(inputs)
    base = EfficientNetB0(include_top=False, weights="imagenet", input_tensor=x)
    base.trainable = False
    x = layers.GlobalAveragePooling2D()(base.output)
    x = layers.Dropout(0.2)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)
    return keras.Model(inputs, outputs), base

def train_category(cat_name, cfg):
    cat_dir = Path(cfg["root_dir"]) / cat_name
    files, labels, class_names = load_dataset(cat_dir)

    if len(set(labels)) < 2:
        return None

    idx = list(range(len(files)))
    random.shuffle(idx)
    split = int(len(idx) * cfg["val_split"])
    val_idx = set(idx[:split])
    train_idx = set(idx[split:])

    def select(arr, idxset):
        return [arr[i] for i in idxset]

    tr_files = select(files, train_idx)
    tr_labels = select(labels, train_idx)
    va_files = select(files, val_idx)
    va_labels = select(labels, val_idx)

    def make_ds(flist, llist):
        ds = tf.data.Dataset.from_tensor_slices((flist, llist))
        ds = ds.map(lambda x, y: preprocess(x, y, cfg["image_size"]), num_parallel_calls=4)
        return ds.batch(cfg["batch_size"]).prefetch(4)

    train_ds = make_ds(tr_files, tr_labels)
    val_ds = make_ds(va_files, va_labels)

    model, base = build_model(len(class_names), cfg["image_size"])

    ckpt = Path(cfg["models_root"]) / cat_name
    ckpt.mkdir(parents=True, exist_ok=True)

    model.compile(
        optimizer=keras.optimizers.Adam(cfg["lr"]),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"]
    )

    model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=cfg["epochs"],
        callbacks=[
            keras.callbacks.ModelCheckpoint(str(ckpt / "best.keras"), save_best_only=True),
            keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True)
        ]
    )

    model.save(ckpt / "final.keras")

    with open(ckpt / "label_map.json", "w", encoding="utf-8") as f:
        json.dump({i: n for i, n in enumerate(class_names)}, f, ensure_ascii=False, indent=2)

    return {
        "category": cat_name,
        "classes": class_names,
        "model_dir": str(ckpt.resolve())
    }

def main():
    random.seed(CONFIG["seed"])
    np.random.seed(CONFIG["seed"])
    tf.random.set_seed(CONFIG["seed"])

    root = Path(CONFIG["root_dir"])
    cats = sorted([d.name for d in root.iterdir() if d.is_dir()])

    registry = {}
    for c in cats:
        info = train_category(c, CONFIG)
        if info:
            registry[c] = info

    out = Path(CONFIG["models_root"]) / "registry_filtered.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
