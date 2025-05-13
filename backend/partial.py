import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from IPython.display import display
from pandas.tseries.offsets import BDay
from scipy.stats import chi2
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from churners import find_churners


def partialRun(
    test_db_path: str,
    output_dir: str,
    cutoff_date: str,
):
    FIXED_DIR = "fixedFiles"

    print("cutoff", cutoff_date)
    print("test_db_path:", test_db_path)
    testt_db = pd.read_excel(test_db_path)
    print(f"Number of rows in the corrected data: {testt_db.shape[0]}")

    train_ratio = 0.80
    sort_column = "Başlangıç T."
    target_col = "Yenileme Durumu"

    testt_db = (
        testt_db.drop(
            columns=["Unnamed: 0", "Müşteri Kodu", "Sözleşme No"], errors="ignore"
        )
        .dropna(subset=[target_col, "Üyelik Adı", sort_column])
        .sort_values(by=sort_column)
        .reset_index(drop=True)
    )

    # Hedef / Özellik ayır
    y = testt_db[target_col].astype(int)
    X = (
        testt_db.drop(columns=[target_col])
        .drop(columns=["Başlangıç T."], errors="ignore")
        .astype(str)
    )

    # --------------------------------------------------
    # 3. ANLAMLI BASE KATEGORİ SEÇİMİ
    # --------------------------------------------------
    base_profile, all_renewal_tables = {}, {}

    for col in X.columns:
        temp = testt_db[[col, target_col]].dropna()
        stats = (
            temp.groupby(col)[target_col]
            .agg(["count", "mean"])
            .rename(columns={"count": "sample_size", "mean": "renewal_rate"})
        )
        stats = stats.sort_values(by="sample_size", ascending=False)
        all_renewal_tables[col] = stats

        median_renewal = stats["renewal_rate"].median()
        closest = stats.iloc[
            (stats["renewal_rate"] - median_renewal).abs().argsort()
        ].index[0]

        base_profile[col] = (
            closest if stats.loc[closest, "sample_size"] >= 500 else stats.index[0]
        )

    # --------------------------------------------------
    # 4. ONE-HOT ENCODER
    # --------------------------------------------------
    categories = [
        [str(base_profile[col])]
        + [
            str(cat)
            for cat in all_renewal_tables[col].index
            if str(cat) != str(base_profile[col])
        ]
        for col in X.columns
    ]

    encoder = OneHotEncoder(
        categories=categories,
        drop="first",
        sparse_output=False,  # scikit-learn >=1.2
        handle_unknown="ignore",
    )

    print("\nSelected Base Categories:")
    for feat, base in base_profile.items():
        print(f"  • {feat}: {base}")

    # Base profili kaydet
    pd.DataFrame(base_profile.items(), columns=["Feature", "Base_Category"]).to_excel(
        os.path.join(output_dir, "base_profile.xlsx"), index=False
    )

    pd.DataFrame(base_profile.items(), columns=["Feature", "Base_Category"]).to_excel(
        os.path.join(FIXED_DIR, "base_profile.xlsx"), index=False
    )

    # --------------------------------------------------
    # 5. ZAMANA DAYALI TRAIN-TEST BÖLÜNÜ
    # --------------------------------------------------
    split_idx = int(len(X) * train_ratio)
    X_train_raw, X_test_raw = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    train_df = pd.concat([X_train_raw, y_train], axis=1).dropna()
    test_df = pd.concat([X_test_raw, y_test], axis=1).dropna()

    X_train, y_train = train_df.drop(columns=target_col), train_df[target_col]
    X_test, y_test = test_df.drop(columns=target_col), test_df[target_col]

    # --------------------------------------------------
    # 6. ÖZELLİK KODLAMA
    # --------------------------------------------------
    X_train_enc = encoder.fit_transform(X_train)
    X_test_enc = encoder.transform(X_test)
    encoded_cols = encoder.get_feature_names_out(X_train.columns)

    X_train_df = pd.DataFrame(X_train_enc, columns=encoded_cols)
    X_test_df = pd.DataFrame(X_test_enc, columns=encoded_cols)

    # --------------------------------------------------
    # 7. LOGISTIC REGRESSION
    # --------------------------------------------------
    log_model = LogisticRegression(random_state=42, max_iter=1000)
    log_model.fit(X_train_df, y_train)

    # --------------------------------------------------
    # 8. DEĞERLENDİRME
    # --------------------------------------------------
    y_pred = log_model.predict(X_test_df)

    print(
        f"\nModel Performansı (Eğitim Oranı: {train_ratio * 100:.0f}%)"
        f"\nAccuracy: {accuracy_score(y_test, y_pred):.4f}"
        f"\nConfusion Matrix:\n{confusion_matrix(y_test, y_pred)}"
        f"\nClassification Report:\n{classification_report(y_test, y_pred)}"
        f"\nIntercept (β₀): {log_model.intercept_[0]:.4f}"
    )

    # --------------------------------------------------
    # 9. KATSAYILARI DIŞA AKTAR
    # --------------------------------------------------
    coefficients_df = pd.DataFrame(
        {"Feature": encoded_cols, "Coefficient": log_model.coef_[0]}
    )

    coeff_path = os.path.join(output_dir, "logistic_regression_coefficients.xlsx")
    coefficients_df.to_excel(coeff_path, sheet_name="Coefficients", index=False)

    print(f"\nCoefficients exported to '{coeff_path}'.")

    # --------------------------------------------------
    # 10. MÜŞTERİ PUANLAMA
    # --------------------------------------------------
    customer_file_path = os.path.join(output_dir, "test_db.xlsx")
    customer_df = pd.read_excel(customer_file_path)

    customer_df = pd.read_excel(customer_file_path)
    cutoff = pd.to_datetime(cutoff_date)

    pending = customer_df[
        customer_df["Yenileme Durumu"].isna()
        & (pd.to_datetime(customer_df["Ek Süreli Bitiş T."], errors="coerce") <= cutoff)
    ].copy()

    # Rename the column for coefficients (keep Feature as column, do NOT set it as index)
    coefficients_df.columns = ["Feature", "Coefficient"]

    # Değerlendirilecek kategorik kolonlar
    selected_cols = [
        "Müşteri Kodu",
        "Üyelik Adı",
        "Cinsiyet",
        "Medeni Durumu",
        "Söz. Türü",
        "Overall Usage Percentage (%)_Range",
        "Last 30 Days Utilization (%)_Range",
        "Average_Visit_Duration_Range",
        "Aranma Sayısı_Range",
        "Unit Price (TL per day)_Range",
        "Renewal Percentage_Range",
        "Sözleşme Yaşı_Range",
    ]

    # Skor tablosu
    customer_scores = pending[["Sözleşme No"] + selected_cols].copy()
    customer_scores["Score"] = log_model.intercept_[0]

    # Skor hesapla
    for feat in selected_cols:
        for i, row in customer_scores.iterrows():
            feat_cat = f"{feat}_{row[feat]}"
            match = coefficients_df.loc[
                coefficients_df["Feature"] == feat_cat, "Coefficient"
            ]
            if not match.empty:
                customer_scores.at[i, "Score"] += match.iloc[0]

    # Olasılık ve sınıf
    customer_scores["Probability"] = 1 / (1 + np.exp(-customer_scores["Score"]))
    customer_scores["Class_0.5"] = (customer_scores["Probability"] >= 0.5).astype(int)

    # Kaydet
    out_path = os.path.join(output_dir, "customer_probabilities_and_classes.xlsx")
    customer_scores.sort_values(by="Probability", ascending=False).to_excel(
        out_path, index=False
    )
    print(f"Results saved to '{out_path}'.")
