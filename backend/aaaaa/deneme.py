import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_curve
)

# 1) Veri yükleme ve ön hazırlık
df = pd.read_excel("excels/testt.xlsx")
df = df.dropna(subset=["Yenileme Durumu", "Üyelik Adı"])

y = df["Yenileme Durumu"].astype(int)
X = df.drop(columns=["Yenileme Durumu", 
                     "Müşteri Kodu","Sözleşme No",
                     "Başlangıç T.","Ek Süreli Bitiş T.",
                     "Sözleşme Durumu","Sözleşme Detay Durumu",
                     "Söz. Türü","Adjusted Tutar"], errors="ignore")

# 2) Özellikleri ayır: kategorik ve sayısal
categorical_cols = [
    "Üyelik Adı","Cinsiyet","Medeni Durumu","Üyelik Tipi",
    "Aday Türü_x","Assigned Interval","Sözleşme Yaşı_Range",
    "Aranma Sayısı_Range","Overall Usage Percentage (%)_Range",
    "Last 30 Days Utilization (%)_Range",
    "Average_Visit_Duration_Range",
    "Unit Price (TL per day)_Range",
    "Number of Past Renewals_Range","Renewal Percentage_Range"
]
# otomatik sayısal seçimi (hedef hariç)
numeric_cols = [c for c in X.columns 
                if c not in categorical_cols 
                and pd.api.types.is_numeric_dtype(X[c])]

X[categorical_cols] = X[categorical_cols].astype(str)

# 3) Pipeline tanımı
preprocessor = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(drop="first", sparse_output=False, handle_unknown="ignore"),
         categorical_cols),
        ("num", StandardScaler(), numeric_cols)
    ]
)

pipeline = Pipeline([
    ("preproc", preprocessor),
    ("clf", LogisticRegression(
        solver="liblinear",
        class_weight="balanced",
        max_iter=1000
    ))
])

# 4) Eğitim / test
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.3,
    random_state=42,
    stratify=y
)

# 5) Hiperparametre arama
param_grid = {
    "clf__C": [0.01, 0.1, 1, 10],
    "clf__penalty": ["l1", "l2"]
}
grid = GridSearchCV(
    pipeline, param_grid,
    cv=5,
    scoring="average_precision",
    n_jobs=-1
)
grid.fit(X_train, y_train)

print("En iyi parametreler:", grid.best_params_)
best_model = grid.best_estimator_

# 6) Olasılık tahminleri ve eşik optimizasyonu
y_prob = best_model.predict_proba(X_test)[:, 1]
precision, recall, thresholds = precision_recall_curve(y_test, y_prob)
f1_scores = 2 * precision * recall / (precision + recall + 1e-8)
best_idx = np.nanargmax(f1_scores)
best_threshold = thresholds[best_idx]
print(f"En iyi F1 skoru elde eden threshold: {best_threshold:.3f}")

# 7) Nihai sınıf tahminleri ve raporlama
y_pred = (y_prob >= best_threshold).astype(int)
print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))
print("Classification Report:\n", classification_report(y_test, y_pred))

# --- Modeli yeni müşterilere uygulama örneği ---
# pending_customers: DataFrame, Yenileme Durumu boş ve bitiş tarihi <= cutoff
# customer_X = pending_customers[X.columns]  # aynı sütun sırası
# customer_prob = best_model.predict_proba(customer_X)[:,1]
# customer_pred = (customer_prob >= best_threshold).astype(int)
# pending_customers["Renewal_Prob"] = customer_prob
# pending_customers["Renewal_Pred"] = customer_pred
