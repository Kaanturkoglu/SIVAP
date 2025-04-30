import pandas as pd
import os
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
from IPython.display import display
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")

# --- Dosya yolları ---
file_path = r"excels/testt.xlsx"
customer_file_path = r"excels/test_db.xlsx"
file_recent = r"excels/yeni.xlsx"
output_dir = "fameo"
os.makedirs(output_dir, exist_ok=True)

# --- Ana veri seti ---
testt_db = pd.read_excel(file_path)
testt_db = testt_db.dropna(subset=["Yenileme Durumu", "Üyelik Adı"])

# Hedef ve özellikleri ayır
y = testt_db["Yenileme Durumu"].astype(int)
X = testt_db.drop(columns=["Yenileme Durumu"])

# --- Kategorik sütunları one-hot encode et ---
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

X_encoded = pd.get_dummies(
    X[categorical_columns], prefix=categorical_columns, drop_first=True
)

# Temel müşteri profili (Base Category)
basis_profile = {}
for col in categorical_columns:
    categories = X[col].astype(str).unique()
    dummies = pd.get_dummies(X[[col]], prefix=col, drop_first=True).columns
    dummy_categories = [c.split("_", 1)[-1] for c in dummies if c.startswith(col + "_")]
    basis_category = list(set(categories) - set(dummy_categories))
    basis_profile[col] = (
        sorted(basis_category)[0] if basis_category else sorted(categories)[0]
    )

print("🧠 Basis Customer Profile:")
for feature, base_value in basis_profile.items():
    print(f"- {feature}: {base_value}")

# Encode edilmiş veriyi birleştir
X = pd.concat([X.drop(columns=categorical_columns), X_encoded], axis=1)

# Gereksiz sütunları çıkar
columns_to_drop = [
    "Müşteri Kodu",
    "Sözleşme No",
    "Başlangıç T.",
    "Ek Süreli Bitiş T.",
    "Sözleşme Durumu",
    "Sözleşme Detay Durumu",
    "Söz. Türü",
    "Adjusted Tutar",
]
X = X.drop(columns=columns_to_drop, errors="ignore")

# --- Eğitim/test bölünmesi ---
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)

# --- Lojistik regresyon modeli ---
log_model = LogisticRegression(random_state=42, max_iter=1000)
log_model.fit(X_train, y_train)

# --- Değerlendirme ---
y_pred = log_model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
conf_matrix = confusion_matrix(y_test, y_pred)
report = classification_report(y_test, y_pred)
intercept = log_model.intercept_[0]

print(f"\nModel Performansı (Eğitim Oranı: 70%)")
print(f"Accuracy: {accuracy:.4f}")
print(f"Confusion Matrix:\n{conf_matrix}")
print(f"Classification Report:\n{report}")
print(f"Intercept (β₀): {intercept:.4f}")

# --- Katsayıları dışa aktar ---
coefficients_df = pd.DataFrame(
    {"Feature": X_train.columns, "Coefficient": log_model.coef_[0]}
)
coefficients_df.to_excel(
    os.path.join(output_dir, "logistic_regression_coefficients.xlsx"),
    sheet_name="Coefficients",
    index=False,
)
print("✅ Coefficients exported.")

# --- Bekleyen müşterilere olasılık puanı atama ---
customer_df = pd.read_excel(customer_file_path)
cutoff_date = pd.to_datetime("2025-01-01")

pending_customers = customer_df[
    customer_df["Yenileme Durumu"].isna()
    & (
        pd.to_datetime(customer_df["Ek Süreli Bitiş T."], errors="coerce")
        <= cutoff_date
    )
].copy()

# Katsayıları yükle ve indeksle
coefficients_df.set_index("Feature", inplace=True)

# Skor hesaplaması için kolonlar
selected_columns = categorical_columns.copy()
customer_scores = pending_customers[["Müşteri Kodu"] + selected_columns].copy()
customer_scores["Score"] = intercept

# Skor hesapla
for feature in selected_columns:
    for i, row in customer_scores.iterrows():
        key = f"{feature}_{row[feature]}"
        if key in coefficients_df.index:
            customer_scores.at[i, "Score"] += coefficients_df.loc[key, "Coefficient"]

# Olasılık ve sınıf
customer_scores["Probability"] = 1 / (1 + np.exp(-customer_scores["Score"]))
customer_scores["Class_0.5"] = (customer_scores["Probability"] >= 0.5).astype(int)

# Kaydet
output_file = os.path.join(output_dir, "customer_probabilities_and_classes.xlsx")
customer_scores.sort_values(by="Probability", ascending=False).to_excel(
    output_file, index=False
)
print(f"✅ Probabilities saved to '{output_file}'.")

# --- Yeniden sözleşme yapanları tespit et ---
df_expiring = pd.read_excel(output_file)
df_recent = pd.read_excel(file_recent)

df_recent["Başlangıç T."] = pd.to_datetime(
    df_recent["Başlangıç T."], dayfirst=True, errors="coerce"
)
df_recent["Ek Süreli Bitiş T."] = pd.to_datetime(
    df_recent["Ek Süreli Bitiş T."], dayfirst=True, errors="coerce"
)

expiring_codes = df_expiring["Müşteri Kodu"].unique()
df_rec_sub = df_recent[df_recent["Müş. Kodu"].isin(expiring_codes)]
df_latest = df_rec_sub.sort_values(
    "Ek Süreli Bitiş T.", ascending=False
).drop_duplicates("Müş. Kodu")

mask = (df_latest["Ek Süreli Bitiş T."] > cutoff_date) & (
    df_latest["Söz. Türü"].str.lower().isin(["yenileme", "güncelleme"])
)
df_result = df_latest[mask]

# --- Karşılaştırma ve sonuç dosyası ---
comparison_excel = df_expiring.copy()
comparison_excel["eşleşme"] = (
    comparison_excel["Müşteri Kodu"].isin(df_result["Müş. Kodu"]).astype(int)
)
comparison_excel["class_eslesme"] = (
    comparison_excel["Class_0.5"] == comparison_excel["eşleşme"]
).astype(int)

comparison_excel.to_excel(os.path.join(output_dir, "comparison.xlsx"), index=False)
print(f"🔍 Comparison saved. Toplam eşleşme: {comparison_excel['eşleşme'].sum()}")
