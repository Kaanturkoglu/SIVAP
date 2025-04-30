import pandas as pd
import numpy as np
import re
from datetime import datetime
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import xgboost as xgb


# — Helper: sütun adlarını temizler —
def sanitize_columns(cols):
    return [re.sub(r"[^0-9A-Za-z_]", "_", c) for c in cols]


# --- 1) Veri Yükleme ve Önişleme ---

# Excel’den oku
testt_db = pd.read_excel(r"excels/testt.xlsx")

# Eksik satırları at
testt_db = testt_db.dropna(subset=["Yenileme Durumu", "Üyelik Adı"])

# Hedef ve özellikleri ayır
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

# One‐hot encode (drop_first=True)
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

# Orijinal kategorik sütunları çıkar, encoded ekle
X = pd.concat([X.drop(columns=categorical_columns), X_encoded], axis=1)

# Sütun adlarını sanitize et
X.columns = sanitize_columns(X.columns)

# Orijinal meta sütunları düş
original_to_drop = [
    "Müşteri Kodu",
    "Sözleşme No",
    "Başlangıç T.",
    "Ek Süreli Bitiş T.",
    "Sözleşme Durumu",
    "Sözleşme Detay Durumu",
    "Söz. Türü",
    "Adjusted Tutar",
]
X = X.drop(columns=sanitize_columns(original_to_drop), errors="ignore")

# Eğitim–test bölünmesi
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)

# NumPy dizilerine çevir (DataFrame dtypes sorununu aşmak için)
X_train_np = X_train.values
X_test_np = X_test.values

# --- 2) XGBoost ile Hyperparameter Tuning ---

xgb_clf = xgb.XGBClassifier(
    use_label_encoder=False, eval_metric="logloss", random_state=42
)

param_dist = {
    "n_estimators": [50, 100, 200, 300],
    "max_depth": [3, 5, 7, 9],
    "learning_rate": [0.01, 0.05, 0.1, 0.2],
    "subsample": [0.6, 0.8, 1.0],
    "colsample_bytree": [0.6, 0.8, 1.0],
    "gamma": [0, 1, 5],
    "reg_alpha": [0, 0.1, 1],
    "reg_lambda": [1, 5, 10],
}

rand_search = RandomizedSearchCV(
    xgb_clf,
    param_distributions=param_dist,
    n_iter=50,
    scoring="accuracy",
    cv=3,
    verbose=1,
    n_jobs=-1,
    random_state=42,
    error_score="raise",
)

# Burada numpy dizisini veriyoruz
rand_search.fit(X_train_np, y_train)
best_model = rand_search.best_estimator_

# --- 3) Model Değerlendirme ---

y_pred = best_model.predict(X_test_np)
y_prob = best_model.predict_proba(X_test_np)[:, 1]

print("Accuracy:", accuracy_score(y_test, y_pred))
print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))
print("Classification Report:\n", classification_report(y_test, y_pred))

# --- 4) Bekleyen Müşterilere Tahmin Uygulama ---

customer_df = pd.read_excel(r"excels/test_db.xlsx")
cutoff_date = pd.to_datetime("2025-01-01")

pending_customers = customer_df[
    customer_df["Yenileme Durumu"].isna()
    & (
        pd.to_datetime(customer_df["Ek Süreli Bitiş T."], errors="coerce")
        <= cutoff_date
    )
].copy()

# One‐hot encode + kolon hizalama
pending_raw = pending_customers[categorical_columns].astype(str)
pending_encoded = pd.get_dummies(
    pending_raw, prefix=categorical_columns, drop_first=True
)
pending_encoded.columns = sanitize_columns(pending_encoded.columns)

# Feature matrix’i oluştur
feature_cols = X_train.columns.tolist()
X_pending = pd.DataFrame(
    0.0, index=pending_encoded.index, columns=feature_cols, dtype=np.float32
)
for col in pending_encoded.columns:
    if col in X_pending.columns:
        X_pending[col] = pending_encoded[col].astype(np.float32)

# Burada numpy dizisini kullanıyoruz
X_pending_np = X_pending.values
y_prob_pending = best_model.predict_proba(X_pending_np)[:, 1]
y_pred_pending = (y_prob_pending >= 0.5).astype(int)

customer_scores = pending_customers[["Müşteri Kodu"]].copy()
customer_scores["Probability"] = y_prob_pending
customer_scores["Class_0.5"] = y_pred_pending

output_file = r"fameo/customer_probabilities_and_classes.xlsx"
customer_scores.sort_values("Probability", ascending=False).to_excel(
    output_file, index=False
)
print(f"Results saved to {output_file}")

# --- 5) Yeni–Eski Renewal Eşleştirme ve Karşılaştırma ---

df_expiring = pd.read_excel(output_file)
df_recent = pd.read_excel(r"excels/yeni.xlsx")

df_recent["Başlangıç T."] = pd.to_datetime(
    df_recent["Başlangıç T."], dayfirst=True, errors="coerce"
)
df_recent["Ek Süreli Bitiş T."] = pd.to_datetime(
    df_recent["Ek Süreli Bitiş T."], dayfirst=True, errors="coerce"
)

end_date = pd.to_datetime("2025-01-01")

expiring_codes = df_expiring["Müşteri Kodu"].unique()
df_rec_sub = df_recent[df_recent["Müş. Kodu"].isin(expiring_codes)]
df_latest = df_rec_sub.sort_values(
    "Ek Süreli Bitiş T.", ascending=False
).drop_duplicates(subset="Müş. Kodu", keep="first")

mask = (df_latest["Ek Süreli Bitiş T."] > end_date) & (
    df_latest["Söz. Türü"].str.lower().isin(["yenileme", "güncelleme"])
)
df_result = df_latest[mask]

output_path1 = r"fameo/Yeni-Eski Renewal.xlsx"
df_result.to_excel(output_path1, index=False)
print(f"Saved {len(df_result)} rows to {output_path1}")

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
