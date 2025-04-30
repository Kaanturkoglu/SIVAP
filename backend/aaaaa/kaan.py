import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import (
    Conv1D,
    BatchNormalization,
    Dropout,
    Flatten,
    Dense,
    Activation,
    Input,
)
from tensorflow.keras.callbacks import EarlyStopping
import keras_tuner as kt

# --- 1) Veri Yükleme ve Önişleme ---

# Dosyaları oku
testt_db = pd.read_excel(r"excels/testt.xlsx")

# Eksikleri at
testt_db = testt_db.dropna(subset=["Yenileme Durumu", "Üyelik Adı"])

# Hedef ve özellikler
y = testt_db["Yenileme Durumu"].astype(int)
X = testt_db.drop(columns=["Yenileme Durumu"])

# Kategorik sütunlar
categorical_columns = [
    "Üyelik Adı",
    "Cinsiyet",
    "Medeni Durumu",
    "Üyelik Tipi",
    "Aday Türü_x",
    "Assigned Interval",
    "Sözleşme Yaşı_Range",
    "Aranma Sayısı_Range",
    "Overall Usage Percentage (%)_Range",
    "Last 30 Days Utilization (%)_Range",
    "Average_Visit_Duration_Range",
    "Unit Price (TL per day)_Range",
    "Number of Past Renewals_Range",
    "Renewal Percentage_Range",
]

# One-hot encoding (drop_first=True)
X_encoded = pd.get_dummies(
    X[categorical_columns], prefix=categorical_columns, drop_first=True
)

# 🔍 Basis profil çıkarımı
basis_profile = {}
for col in categorical_columns:
    cats = X[col].astype(str).unique()
    dummies = pd.get_dummies(X[[col]], prefix=col, drop_first=True).columns
    dummy_cats = [d.split("_", 1)[-1] for d in dummies if d.startswith(col + "_")]
    base = list(set(cats) - set(dummy_cats))
    basis_profile[col] = sorted(base)[0] if base else sorted(cats)[0]

print("🧠 Basis Customer Profile:")
for feat, val in basis_profile.items():
    print(f"- {feat}: {val}")

# Orijinal kategorik sütunları at, encoded ekle
X = pd.concat([X.drop(columns=categorical_columns), X_encoded], axis=1)

# Kullanılmayacak sütunlar
to_drop = [
    "Müşteri Kodu",
    "Sözleşme No",
    "Başlangıç T.",
    "Ek Süreli Bitiş T.",
    "Sözleşme Durumu",
    "Sözleşme Detay Durumu",
    "Söz. Türü",
    "Adjusted Tutar",
]
X = X.drop(columns=to_drop, errors="ignore")

# Eğitim/test böl
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)

# CNN için reshape: (örnek, özellik, kanal=1)
n_features = X_train.shape[1]
X_train_cnn = X_train.values.reshape(-1, n_features, 1)
X_test_cnn = X_test.values.reshape(-1, n_features, 1)

# --- 2) Hyperparameter Tuning için Model Builder ---


def build_model(hp):
    model = Sequential()
    model.add(Input(shape=(n_features, 1)))

    # Kaç adet Conv katmanı?
    for i in range(hp.Int("conv_layers", 1, 3)):
        model.add(
            Conv1D(
                filters=hp.Choice(f"filters_{i}", [16, 32, 64]),
                kernel_size=hp.Choice(f"kernel_{i}", [3, 5, 7]),
                activation="relu",
                padding="same",
            )
        )
        model.add(BatchNormalization())
        model.add(Dropout(hp.Float(f"dropout_{i}", 0.1, 0.5, step=0.1)))

    model.add(Flatten())
    model.add(Dense(units=hp.Int("dense_units", 8, 32, step=8), activation="relu"))
    model.add(Dropout(hp.Float("dropout_dense", 0.1, 0.5, step=0.1)))
    model.add(Dense(1, activation="sigmoid"))

    model.compile(
        optimizer=hp.Choice("optimizer", ["adam", "rmsprop", "sgd"]),
        loss="binary_crossentropy",
        metrics=["accuracy"],
    )
    return model


tuner = kt.Hyperband(
    build_model,
    objective="val_accuracy",
    max_epochs=30,
    factor=3,
    directory="tuner_dir",
    project_name="renewal_cnn",
)

# EarlyStopping callback
es = EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)

# Aramayı başlat
tuner.search(
    X_train_cnn, y_train, epochs=30, validation_split=0.2, callbacks=[es], verbose=1
)

# En iyi modeli al
best_model = tuner.get_best_models(num_models=1)[0]

# --- 3) Değerlendirme ---

# Test seti üzerinde tahmin
y_prob = best_model.predict(X_test_cnn).flatten()
y_pred = (y_prob >= 0.5).astype(int)

# Metrikler
acc = accuracy_score(y_test, y_pred)
cm = confusion_matrix(y_test, y_pred)
report_str = classification_report(y_test, y_pred)

print(f"Test Accuracy: {acc:.4f}")
print("Confusion Matrix:\n", cm)
print("Classification Report:\n", report_str)


# --- (Önceki adımlarda tuner ile en iyi modeli elde ettiğinizi varsayıyoruz) ---
# best_model, n_features, categorical_columns gibi değişkenler tanımlı olmalı

# 1) Bekleyen müşterileri yükle ve filtrele
customer_file_path = r"excels/test_db.xlsx"
customer_df = pd.read_excel(customer_file_path)

cutoff_date = pd.to_datetime("2025-01-01")
pending_customers = customer_df[
    customer_df["Yenileme Durumu"].isna()
    & (
        pd.to_datetime(customer_df["Ek Süreli Bitiş T."], errors="coerce")
        <= cutoff_date
    )
].copy()

# 2) Aynı one-hot encoding adımlarını uygula ve feature matrisini oluştur
#    X_train.columns listesine göre dummy sütunları hizala
feature_cols = X_train.columns.tolist()

# Kategorik sütunlardan sadece string elde et
pending_raw = pending_customers[categorical_columns].astype(str)

# One‐hot encode (drop_first=True)
pending_encoded = pd.get_dummies(
    pending_raw, prefix=categorical_columns, drop_first=True
)

# Boş bir dataframe oluştur, tüm feature_cols'u içerir
X_pending = pd.DataFrame(0, index=pending_encoded.index, columns=feature_cols)

X_pending = pd.DataFrame(
    0.0,
    index=pending_encoded.index,
    columns=feature_cols,
    dtype=np.float32
)

# Gerçek dummy sütunlarını yerleştir
for col in pending_encoded.columns:
    if col in X_pending.columns:
        X_pending[col] = pending_encoded[col].astype(np.float32)

# 3) CNN’e uygun shape’e getir
X_pending_cnn = X_pending.values.astype(np.float32).reshape(-1, n_features, 1)

# 4) Olasılık ve sınıf tahmini
y_prob_pending = best_model.predict(X_pending_cnn).flatten()
y_pred_pending = (y_prob_pending >= 0.5).astype(int)

# 5) Sonuçları DataFrame’e al ve kaydet
customer_scores = pending_customers[["Müşteri Kodu"]].copy()
customer_scores["Probability"] = y_prob_pending
customer_scores["Class_0.5"] = y_pred_pending

output_file = r"fameo/customer_probabilities_and_classes.xlsx"
customer_scores.sort_values("Probability", ascending=False).to_excel(
    output_file, index=False
)
print(f"Results saved to {output_file}")

# 6) Yeni ve eski kayıtları eşleştir
file_expiring = output_file
file_recent = r"excels/yeni.xlsx"

df_expiring = pd.read_excel(file_expiring)
df_recent = pd.read_excel(file_recent)

# Tarih sütunlarını datetime’a çevir
df_recent["Başlangıç T."] = pd.to_datetime(
    df_recent["Başlangıç T."], dayfirst=True, errors="coerce"
)
df_recent["Ek Süreli Bitiş T."] = pd.to_datetime(
    df_recent["Ek Süreli Bitiş T."], dayfirst=True, errors="coerce"
)

end_date = pd.to_datetime("2025-01-01")

# Expiring kod listesi
expiring_codes = df_expiring["Müşteri Kodu"].unique()

# Son kayıtları al
df_rec_sub = df_recent[df_recent["Müş. Kodu"].isin(expiring_codes)]
df_latest = df_rec_sub.sort_values(
    "Ek Süreli Bitiş T.", ascending=False
).drop_duplicates(subset="Müş. Kodu", keep="first")

# Filtre: bitiş tarihine ve tür yenileme/güncelleme
mask = (df_latest["Ek Süreli Bitiş T."] > end_date) & (
    df_latest["Söz. Türü"].str.lower().isin(["yenileme", "güncelleme"])
)
df_result = df_latest[mask]

# Yeni-Eski Renewal kaydet
output_path1 = r"fameo/Yeni-Eski Renewal.xlsx"
df_result.to_excel(output_path1, index=False)
print(f"Saved {len(df_result)} rows to {output_path1}")

# 7) Eşleşme kontrolü ve karşılaştırma
comparison_excel = df_expiring.copy()
col_exp = [c for c in comparison_excel.columns if "müş" in c.lower()][0]
col_res = [c for c in df_result.columns if "müş" in c.lower()][0]

comparison_excel["eşleşme"] = (
    comparison_excel[col_exp].isin(df_result[col_res]).astype(int)
)

comparison_excel["class_eslesme"] = (
    comparison_excel["Class_0.5"] == comparison_excel["eşleşme"]
).astype(int)

output_path2 = r"fameo/comparison.xlsx"
comparison_excel.to_excel(output_path2, index=False)
print(f"Comparison saved to {output_path2}")
