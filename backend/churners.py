import pandas as pd
import os
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import warnings

warnings.filterwarnings("ignore")

def find_churners(
    customer_file_path: str,
    file_recent: str,
    output_dir: str,
    coefficients_file_path: str,
    intercept: float,
    categorical_columns: list[str]
):
    os.makedirs(output_dir, exist_ok=True)

    customer_df = pd.read_excel(customer_file_path)
    cutoff = pd.to_datetime("2025-01-01")

    pending = customer_df[
        customer_df["Yenileme Durumu"].isna() &
        (pd.to_datetime(customer_df["Ek Süreli Bitiş T."], errors="coerce") <= cutoff)
    ].copy()

    coef_df = pd.read_excel(coefficients_file_path)
    coef_df.set_index("Feature", inplace=True)
    scores = pending[["Müşteri Kodu"] + categorical_columns].copy()
    scores["Score"] = intercept

    for col in categorical_columns:
        for i, row in scores.iterrows():
            key = f"{col}_{row[col]}"
            if key in coef_df.index:
                scores.at[i, "Score"] += coef_df.loc[key, "Coefficient"]

    scores["Probability"] = 1 / (1 + np.exp(-scores["Score"]))
    scores["Class_0.5"] = (scores["Probability"] >= 0.5).astype(int)

    result_path = os.path.join(output_dir, "customer_probabilities_and_classes.xlsx")
    scores.sort_values("Probability", ascending=False).to_excel(result_path, index=False)

    # 2. Detect renewed contracts
    df_exp = pd.read_excel(result_path)
    df_new = pd.read_excel(file_recent)

    df_new["Başlangıç T."] = pd.to_datetime(df_new["Başlangıç T."], errors="coerce", dayfirst=True)
    df_new["Ek Süreli Bitiş T."] = pd.to_datetime(df_new["Ek Süreli Bitiş T."], errors="coerce", dayfirst=True)

    codes = df_exp["Müşteri Kodu"].unique()
    df_sub = df_new[df_new["Müş. Kodu"].isin(codes)]
    df_latest = df_sub.sort_values("Ek Süreli Bitiş T.", ascending=False).drop_duplicates("Müş. Kodu")

    renewed = df_latest[
        (df_latest["Ek Süreli Bitiş T."] > cutoff) &
        (df_latest["Söz. Türü"].str.lower().isin(["yenileme", "güncelleme"]))
    ]

    df_exp["eşleşme"] = df_exp["Müşteri Kodu"].isin(renewed["Müş. Kodu"]).astype(int)
    df_exp["class_eslesme"] = (df_exp["Class_0.5"] == df_exp["eşleşme"]).astype(int)

    final_path = os.path.join(output_dir, "comparison.xlsx")
    df_exp.to_excel(final_path, index=False)

    print(f"🔍 Comparison saved to {final_path} | Eşleşme sayısı: {df_exp['eşleşme'].sum()}")
