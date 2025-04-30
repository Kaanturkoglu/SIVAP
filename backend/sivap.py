import pandas as pd
import os
from datetime import datetime
import numpy as np
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from scipy.stats import chi2
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
from pandas.tseries.offsets import BDay
from datetime import timedelta
from IPython.display import display
import requests
import io


def process_excel_files(
    uyelik_sozlesmeleri_path: str,
    musteriler_path: str,
    iptal_listesi_path: str,
    aktiviteler_dir: str,
    giriş_çıkış_dir: str,
    output_dir: str,
):
    FIXED_DIR = "fixedFiles"

    # merge söz ve müş
    uyelik_sozlesmeleri_path = uyelik_sozlesmeleri_path
    musteriler_path = musteriler_path
    uyelik_sozlesmeleri = pd.read_excel(uyelik_sozlesmeleri_path)
    musteriler = pd.read_excel(musteriler_path)
    uyelik_sozlesmeleri.rename(columns={"Müş. Kodu": "Müşteri Kodu"}, inplace=True)
    musteriler.rename(columns={"Müş. Kodu": "Müşteri Kodu"}, inplace=True)
    merged_data = pd.merge(
        uyelik_sozlesmeleri, musteriler, on="Müşteri Kodu", how="left"
    )

    # "PERSONEL" sil
    cleaned_data = merged_data[merged_data["Üyelik Adı"] != "PERSONEL"]

    # Doğum Tarihi eksik olanlara mean atama
    cleaned_data.loc[:, "Doğum Tarihi_x"] = pd.to_datetime(
        cleaned_data["Doğum Tarihi_x"], errors="coerce"
    )
    mean_dogum_tarihi = cleaned_data["Doğum Tarihi_x"].dropna().mean()
    cleaned_data.loc[:, "Doğum Tarihi_x"] = cleaned_data["Doğum Tarihi_x"].fillna(
        mean_dogum_tarihi
    )

    # tarihleri datetime yapma
    cleaned_data = cleaned_data.copy()

    cleaned_data.loc[:, "Satış Tarihi"] = pd.to_datetime(
        cleaned_data["Satış Tarihi"], errors="coerce"
    )
    cleaned_data.loc[:, "Doğum Tarihi_x"] = pd.to_datetime(
        cleaned_data["Doğum Tarihi_x"], errors="coerce"
    )

    # Sözleşme Yaşı bulma işi
    cleaned_data.loc[:, "Sözleşme Yaşı"] = cleaned_data.apply(
        lambda row: (row["Satış Tarihi"] - row["Doğum Tarihi_x"]).days // 365
        if pd.notnull(row["Satış Tarihi"]) and pd.notnull(row["Doğum Tarihi_x"])
        else None,
        axis=1,
    )

    # "Medeni Durumu" kolonunda boş olanları "Belirtilmemiş" olarak doldur
    cleaned_data.loc[:, "Medeni Durumu"] = cleaned_data["Medeni Durumu"].fillna(
        "Belirtilmemiş"
    )

    # "Sözleşme No" değerinin içinde "-S" geçen satırların "Medeni Durumu" kolonunu "Evli" olarak güncelle
    cleaned_data.loc[
        cleaned_data["Sözleşme No"].str.contains("-S", na=False), "Medeni Durumu"
    ] = "Evli"

    # "Üyelik Tipi" kolonunda "Asil Üyelik" olan satırların "Medeni Durumu" kolonunu "Evli" olarak güncelle
    cleaned_data.loc[cleaned_data["Üyelik Tipi"] == "Asil Üyelik", "Medeni Durumu"] = (
        "Evli"
    )

    # "Sözleşme No" değerinin sonunda "-" ve bir rakam varsa "Medeni Durumu" kolonunu "Bekar" olarak güncelle
    cleaned_data.loc[
        cleaned_data["Sözleşme No"].str.match(r".*-\d$", na=False), "Medeni Durumu"
    ] = "Bekar"

    # Gereksiz ve duplicate kolonları silme
    columns_to_drop = [
        "Bitiş T.",
        "Doğum Tarihi_x",
        "Dondurma Süresi",
        "Ek Süre",
        "Kalan Gün Sayısı",
        "Satış Danışmanı_x",
        "Split Danışmanı_x",
        "Şube_y",
        "Aktif",
        "Üyelik Durumu",
        "Müşteri Grubu_y",
        "Cinsiyeti",
        "Yaş",
        "Satış Danışmanı_y",
        "Split Danışmanı_y",
        "Aday Türü_y",
        "Adaydan Müşteriye Dönüşme Tarihi",
        "Doğum Tarihi_y",
        "Kayıt Tarihi",
    ]
    cleaned_data = cleaned_data.drop(columns=columns_to_drop, errors="ignore")

    # İptal listesini yükleme
    file2 = iptal_listesi_path
    data2 = pd.read_excel(file2)
    data2.rename(columns={"Sözleşme No.": "Sözleşme No"}, inplace=True)
    merged_data = pd.merge(
        cleaned_data,
        data2[["Sözleşme No", "İptal Sebebi"]],
        on="Sözleşme No",
        how="left",
    )
    merged_data["İptal Sebebi"] = merged_data["İptal Sebebi"].str.strip()

    # "İptal Sebebi"  "HATALI KAYIT" olanları silme
    final_data = merged_data[merged_data["İptal Sebebi"] != "HATALI KAYIT"]

    # datetime doğrulama
    final_data.loc[:, "Başlangıç T."] = pd.to_datetime(
        final_data["Başlangıç T."], errors="coerce"
    )
    final_data.loc[:, "Ek Süreli Bitiş T."] = pd.to_datetime(
        final_data["Ek Süreli Bitiş T."], errors="coerce"
    )

    # Yenilendi mi?
    def check_renewal(df):
        renewal_status = []
        for i in range(len(df)):
            current_customer = df.loc[i, "Müşteri Kodu"]
            current_status = df.loc[i, "Sözleşme Durumu"]
            current_type = df.loc[i, "Söz. Türü"]

            if i < len(df) - 1 and df.loc[i + 1, "Müşteri Kodu"] == current_customer:
                next_type = df.loc[i + 1, "Söz. Türü"]
                next_status = df.loc[i + 1, "Sözleşme Durumu"]
                if current_status == "Kapandı" and (
                    next_type == "Yenileme" or next_type == "Güncelleme"
                ):
                    renewal_status.append(1)
                elif next_status == "Başlamadı":
                    renewal_status.append(1)
                else:
                    renewal_status.append(0)
            else:
                if current_status == "Aktif":
                    renewal_status.append(None)
                else:
                    renewal_status.append(0)

        while len(renewal_status) < len(df):
            renewal_status.append(None)

        df["Yenileme Durumu"] = renewal_status
        return df

    final_data = final_data.sort_values(
        by=["Müşteri Kodu", "Başlangıç T."]
    ).reset_index(drop=True)
    final_data = check_renewal(final_data)

    # Update "Sözleşme Yaşı" for rows with "Üyelik Tipi" == "Bireysel Üyelik" and "Sözleşme Yaşı" < 18
    mean_age = final_data["Sözleşme Yaşı"].mean()
    final_data.loc[
        (final_data["Üyelik Tipi"] == "Bireysel Üyelik")
        & (final_data["Sözleşme Yaşı"] < 18),
        "Sözleşme Yaşı",
    ] = int(mean_age)

    # Giriş-Çıkış okuma ve hesaplama
    excel_folder = giriş_çıkış_dir
    excel_files = [
        os.path.join(excel_folder, file)
        for file in os.listdir(excel_folder)
        if file.endswith((".xls", ".xlsx"))
    ]
    combined_data = pd.DataFrame()
    for file in excel_files:
        try:
            df = pd.read_excel(file)
            columns_to_drop = [
                "Aktif",
                "Üyelik Durumu",
                "Söz. Durumu",
                "Üyelik Sözleşmesi Detay Durumu",
                "Mekan",
                "Geç Çıkış Süresi(Dk.)",
                "Giris Cihazı",
                "Çıkış Cihazı",
                "İptal Tarihi",
            ]
            df = df.drop(
                columns=[col for col in columns_to_drop if col in df.columns],
                errors="ignore",
            )
            df["Giriş Zamanı"] = pd.to_datetime(
                df["Giriş Saati"], format="%H:%M", errors="coerce"
            ).dt.time
            df["Çıkış Zamanı"] = pd.to_datetime(
                df["Çıkış Saati"], format="%H:%M", errors="coerce"
            ).dt.time

            def calculate_duration(row):
                if pd.notnull(row["Giriş Zamanı"]) and pd.notnull(row["Çıkış Zamanı"]):
                    entrance = datetime.combine(datetime.min, row["Giriş Zamanı"])
                    exit = datetime.combine(datetime.min, row["Çıkış Zamanı"])
                    return (exit - entrance).seconds / 60
                return None

            df["Kalış Süresi"] = df.apply(calculate_duration, axis=1)

            df = df[df["Kalış Süresi"] >= 15]
            df = df.drop(
                columns=["Giriş Saati", "Çıkış Saati", "Giriş Zamanı", "Çıkış Zamanı"],
                errors="ignore",
            )
            combined_data = pd.concat([combined_data, df], ignore_index=True)

            print(f"Processed file: {file}")

        except Exception as e:
            print(f"Error processing file {file}: {e}")

    omer_file = combined_data

    # Müşteri Kodu ve Sözleşme No eşleştirme
    membership_map = (
        omer_file.loc[omer_file["Üyelik"].notnull()]
        .set_index("Kodu")["Üyelik"]
        .to_dict()
    )
    omer_file["Üyelik"] = omer_file["Üyelik"].fillna(
        omer_file["Kodu"].map(membership_map)
    )

    # NaN Üyelik No'larını sil
    goksun_data = omer_file[~omer_file["Üyelik"].isna()]
    goksun_data = goksun_data[goksun_data["Üyelik"] != ""]
    goksun_data = goksun_data[goksun_data["Üyelik"] != "PERSONEL"]

    # Giriş ve Çıkış tarihlerini datetime olarak kontrol etme
    goksun_data.loc[:, "Giriş Tarihi"] = pd.to_datetime(
        goksun_data["Giriş Tarihi"], format="%Y-%m-%d %H:%M:%S.%f", errors="coerce"
    )
    goksun_data.loc[:, "Çıkış Tarihi"] = pd.to_datetime(
        goksun_data["Çıkış Tarihi"], format="%Y-%m-%d %H:%M:%S.%f", errors="coerce"
    )

    # (23:59:59) girişlerini düzeltme
    incorrect_exit_time = (
        goksun_data["Çıkış Tarihi"].dt.time == pd.Timestamp("23:59:59").time()
    )
    goksun_data.loc[:, "Duration (minutes)"] = (
        goksun_data["Çıkış Tarihi"] - omer_file["Giriş Tarihi"]
    ).dt.total_seconds() / 60
    valid_data = goksun_data[~incorrect_exit_time]
    mean_durations = valid_data.groupby("Kodu")["Duration (minutes)"].mean()
    goksun_data.loc[:, "Member Mean Duration (minutes)"] = goksun_data["Kodu"].map(
        mean_durations
    )
    goksun_data.loc[incorrect_exit_time, "Duration (minutes)"] = goksun_data.loc[
        incorrect_exit_time, "Kodu"
    ].map(mean_durations)

    incorrect_exit_time = (
        goksun_data["Çıkış Tarihi"].dt.time == pd.Timestamp("23:59:59").time()
    )

    # Ortalama kalma süresi hesaplama
    overall_mean_duration = goksun_data["Member Mean Duration (minutes)"].mean()

    for index, row in goksun_data[incorrect_exit_time].iterrows():
        member_mean = row["Member Mean Duration (minutes)"]
        duration_to_add = (
            member_mean if pd.notna(member_mean) else overall_mean_duration
        )
        goksun_data.at[index, "Çıkış Tarihi"] = row["Giriş Tarihi"] + pd.to_timedelta(
            duration_to_add, unit="m"
        )

    final_data.loc[:, "Başlangıç T."] = pd.to_datetime(
        final_data["Başlangıç T."], errors="coerce"
    )
    final_data.loc[:, "Ek Süreli Bitiş T."] = pd.to_datetime(
        final_data["Ek Süreli Bitiş T."], errors="coerce"
    )
    goksun_data.loc[:, "Giriş Tarihi"] = pd.to_datetime(
        goksun_data["Giriş Tarihi"], errors="coerce"
    )

    goksun_data["Sözleşme No"] = None

    for i, row in goksun_data.iterrows():
        giris_tarihi = row["Giriş Tarihi"]
        musteri_kodu = row["Kodu"]
        matched_contract = final_data[
            (final_data["Müşteri Kodu"] == musteri_kodu)
            & (final_data["Başlangıç T."] <= giris_tarihi)
            & (final_data["Ek Süreli Bitiş T."] >= giris_tarihi)
        ]
        if not matched_contract.empty:
            goksun_data.at[i, "Sözleşme No"] = matched_contract.iloc[0]["Sözleşme No"]

    # NaN Sözleşme No'ları silme
    sine_data = goksun_data.dropna(subset=["Sözleşme No"])

    # Son Feature'ları depolama
    results = []
    for _, contract in final_data.iterrows():
        member_id = contract["Müşteri Kodu"]
        start_date = contract["Başlangıç T."]
        end_date = contract["Ek Süreli Bitiş T."]
        membership_type = contract["Üyelik Adı"]
        tutar = contract["Tutar ( TL )"]
        sozlesme_no = contract["Sözleşme No"]
        sozlesme_turu = contract["Söz. Türü"]
        sozlesme_durumu = contract["Sözleşme Durumu"]
        soz_de_du = contract["Sözleşme Detay Durumu"]
        cinsiyet = contract["Cinsiyet"]
        med = contract["Medeni Durumu"]
        uyelik_tipi = contract["Üyelik Tipi"]
        aday_turu = contract["Aday Türü_x"]
        sozlesme_yasi = contract["Sözleşme Yaşı"]
        yenilenme_durumu = contract["Yenileme Durumu"]
        contract_usage = sine_data[
            (sine_data["Kodu"] == member_id)
            & (sine_data["Giriş Tarihi"] >= start_date)
            & (sine_data["Giriş Tarihi"] <= end_date)
        ]

        # Total Usage Count
        total_usage = contract_usage.shape[0]

        # 30 days starting from 60 days before the contract ends
        last_30_days_start = end_date - timedelta(days=30)
        last_30_days_usage = contract_usage[
            (contract_usage["Giriş Tarihi"] >= last_30_days_start)
            & (contract_usage["Giriş Tarihi"] <= end_date)
        ]
        last_30_days_count = last_30_days_usage.shape[0]

        # Five Days
        if membership_type in ["FIVE DAYS AİLE", "FIVE DAYS BİREYSEL"]:
            total_possible_days = pd.date_range(
                start=start_date, end=end_date, freq="D"
            )
            max_usage_days = sum(day.weekday() < 5 for day in total_possible_days)
        else:
            max_usage_days = (end_date - start_date).days
        overall_percentage = (
            (total_usage / max_usage_days) * 100 if max_usage_days > 0 else 0
        )
        last_30_days_percentage = (last_30_days_count / 30) * 100

        results.append(
            {
                "Müşteri Kodu": member_id,
                "Üyelik Adı": membership_type,
                "Başlangıç T.": start_date,
                "Ek Süreli Bitiş T.": end_date,
                "Sözleşme No": sozlesme_no,
                "Sözleşme Durumu": sozlesme_durumu,
                "Sözleşme Detay Durumu": soz_de_du,
                "Cinsiyet": cinsiyet,
                "Medeni Durumu": med,
                "Söz. Türü": sozlesme_turu,
                "Üyelik Tipi": uyelik_tipi,
                "Aday Türü_x": aday_turu,
                "Sözleşme Yaşı": sozlesme_yasi,
                "Yenileme Durumu": yenilenme_durumu,
                "Total Usage": total_usage,
                "Last 30 Days Usage Count": last_30_days_count,
                "Overall Usage Percentage (%)": overall_percentage,
                "Last 30 Days Utilization (%)": last_30_days_percentage,
                "Tutar ( TL )": tutar,
            }
        )

    results_df = pd.DataFrame(results)

    sine_data = sine_data.copy()
    sine_data["Giriş Tarihi"] = pd.to_datetime(sine_data["Giriş Tarihi"])
    sine_data["Çıkış Tarihi"] = pd.to_datetime(sine_data["Çıkış Tarihi"])

    # Assigned Interval
    sine_data["Giriş Saat"] = (
        sine_data["Giriş Tarihi"].dt.hour + sine_data["Giriş Tarihi"].dt.minute / 60
    )
    sine_data["Çıkış Saat"] = (
        sine_data["Çıkış Tarihi"].dt.hour + sine_data["Çıkış Tarihi"].dt.minute / 60
    )
    sine_data["Visit Duration (minutes)"] = (
        sine_data["Çıkış Tarihi"] - sine_data["Giriş Tarihi"]
    ).dt.total_seconds() / 60
    sine_data["Midpoint"] = (sine_data["Giriş Saat"] + sine_data["Çıkış Saat"]) / 2

    def map_to_interval(hour):
        if 6 <= hour < 11:
            return "6-11"
        elif 11 <= hour < 15:
            return "11-15"
        elif 15 <= hour < 19:
            return "15-19"
        elif 19 <= hour < 23:
            return "19-23"
        else:
            return "Outside Defined Intervals"

    sine_data["Assigned Interval"] = sine_data["Midpoint"].apply(map_to_interval)
    result = (
        sine_data.groupby("Sözleşme No")
        .agg(
            Üyelik=("Üyelik", "first"),
            Average_Entry_Hour=("Giriş Saat", "mean"),
            Average_Exit_Hour=("Çıkış Saat", "mean"),
            Average_Midpoint=("Midpoint", "mean"),
            Average_Visit_Duration=("Visit Duration (minutes)", "mean"),
        )
        .reset_index()
    )

    def hour_to_time(hour):
        hh = int(hour)
        mm = int((hour - hh) * 60)
        return f"{hh:02d}:{mm:02d}"

    result["Average_Entry_Time"] = result["Average_Entry_Hour"].apply(hour_to_time)
    result["Average_Exit_Time"] = result["Average_Exit_Hour"].apply(hour_to_time)
    result["Average_Midpoint_Time"] = result["Average_Midpoint"].apply(hour_to_time)
    result = result.drop(
        columns=["Average_Entry_Hour", "Average_Exit_Hour", "Average_Midpoint"]
    )
    result["Assigned Interval"] = result["Average_Midpoint_Time"].apply(
        lambda t: map_to_interval(int(t.split(":")[0]))
    )
    results_df = results_df.merge(result, on="Sözleşme No", how="left")
    results_df.head()
    columns_to_drop = [
        "Üyelik",
        "Average_Entry_Time",
        "Average_Exit_Time",
        "Average_Midpoint_Time",
    ]
    results_df = results_df.drop(columns=columns_to_drop, errors="ignore")
    results_df.loc[
        results_df["Total Usage"] == 0, ["Average_Visit_Duration", "Assigned Interval"]
    ] = 0

    # Aktivite Raporlarından Aranma Sayısı bulma
    folder_path = aktiviteler_dir
    all_data = []

    for file_name in os.listdir(folder_path):
        if file_name.endswith(".xlsx") or file_name.endswith(".xls"):
            file_path = os.path.join(folder_path, file_name)
            try:
                df = pd.read_excel(file_path)
                df["Dosya Adı"] = file_name
                all_data.append(df)
            except Exception as e:
                print(f"{file_name} okunurken bir hata oluştu: {e}")

    aranma_data = pd.concat(all_data, ignore_index=True)

    # Datetime doğrulama
    aranma_data["Tarih"] = pd.to_datetime(aranma_data["Tarih"])
    final_data["Başlangıç T."] = pd.to_datetime(final_data["Başlangıç T."])
    final_data["Ek Süreli Bitiş T."] = pd.to_datetime(final_data["Ek Süreli Bitiş T."])
    aranma_data["Sözleşme No"] = None
    for i, call in aranma_data.iterrows():
        müş_kodu = call["Kodu"]
        call_date = call["Tarih"]
        matching_contracts = final_data[
            (final_data["Müşteri Kodu"] == müş_kodu)
            & (final_data["Başlangıç T."] <= call_date)
            & (final_data["Ek Süreli Bitiş T."] >= call_date)
        ]
        if not matching_contracts.empty:
            aranma_data.at[i, "Sözleşme No"] = matching_contracts.iloc[0]["Sözleşme No"]

    sözleşme_counts = aranma_data["Sözleşme No"].value_counts()
    aranma_data["Aranma Sayısı"] = aranma_data["Sözleşme No"].map(sözleşme_counts)

    # Sözleşme No'ya göre Aranma Sayısı eşleştirme
    final_data = final_data.merge(
        aranma_data[["Sözleşme No", "Aranma Sayısı"]], on="Sözleşme No", how="left"
    )
    final_data = final_data.drop_duplicates()
    final_data = final_data.drop_duplicates(subset=["Sözleşme No"])
    results_df = results_df.merge(
        final_data[["Sözleşme No", "Aranma Sayısı"]], on="Sözleşme No", how="left"
    )
    results_df = results_df.dropna(subset=["Assigned Interval"])
    results_df["Aranma Sayısı"] = results_df["Aranma Sayısı"].fillna(0)

    contracts_df = results_df.copy()

    # Download TÜİK CPI Table
    url = "https://data.tuik.gov.tr/Bulten/DownloadIstatistikselTablo?p=VbZnKRKuqHltfgm6LftGQSYqYlk/uPE2vMOyUf0LUPBBo1cKgBWHc1stJWf1n5Mv"
    response = requests.get(url)
    xls = pd.read_excel(
        io.BytesIO(response.content), sheet_name=0, skiprows=4, nrows=21
    )

    # Clean CPI table
    xls.columns = xls.columns.map(str).str.strip()
    xls = xls.dropna(how="all", axis=1).dropna(how="all", axis=0)
    xls.rename(columns={xls.columns[0]: "Year"}, inplace=True)
    xls["Year"] = pd.to_numeric(xls["Year"], errors="coerce")
    cpi_lookup = xls.set_index("Year")

    # Translate month names: English → Turkish
    month_translation = {
        "January": "Ocak",
        "February": "Şubat",
        "March": "Mart",
        "April": "Nisan",
        "May": "Mayıs",
        "June": "Haziran",
        "July": "Temmuz",
        "August": "Ağustos",
        "September": "Eylül",
        "October": "Ekim",
        "November": "Kasım",
        "December": "Aralık",
    }

    # Get latest CPI index from last year
    latest_year = cpi_lookup.index.max()
    latest_row = cpi_lookup.loc[latest_year]
    latest_month = latest_row.dropna().index[-1]
    latest_index = latest_row[latest_month]

    print(f"📌 Latest CPI Index: {latest_index:.2f} ({latest_month} {latest_year})")

    # Your contract data
    # Assuming contracts_df already exists with columns:
    # - 'Başlangıç T.'
    # - 'Tutar ( TL )'

    # Define CPI adjustment function per row
    def apply_cpi_adjustment(row):
        try:
            start_date = pd.to_datetime(row["Başlangıç T."], errors="coerce")
            if pd.isna(start_date) or row["Tutar ( TL )"] == 0:
                return row["Tutar ( TL )"]

            year = start_date.year
            month_idx = start_date.month  # 1=January, 2=February, ..., 12=December

            if year not in cpi_lookup.index:
                return row["Tutar ( TL )"]

            # Get the CPI index for that year and month
            month_col_name = cpi_lookup.columns[month_idx - 1]  # zero-indexed
            start_index = cpi_lookup.loc[year, month_col_name]

            # Reference (latest) index
            latest_index = cpi_lookup.iloc[-1].dropna().values[-1]

            if pd.isna(start_index) or start_index == 0:
                return row["Tutar ( TL )"]

            adjusted = row["Tutar ( TL )"] * (latest_index / start_index)
            return adjusted
        except Exception as e:
            print(f"❌ Error on row: {e}")
            return row["Tutar ( TL )"]

    # Apply to all contracts
    contracts_df["Adjusted Tutar"] = contracts_df.apply(apply_cpi_adjustment, axis=1)

    # Optional: Save
    contracts_df.to_excel("processed/adjusted_contracts_with_cpi.xlsx", index=False)

    # Five Days için ücret
    five_day_memberships = ["FIVE DAYS BİREYSEL", "FIVE DAYS AİLE"]

    def calculate_unit_price(row):
        start_date = pd.to_datetime(row["Başlangıç T."], errors="coerce")
        end_date = pd.to_datetime(row["Ek Süreli Bitiş T."], errors="coerce")
        price = row["Adjusted Tutar"]
        membership_type = row["Üyelik Adı"]
        if pd.isna(start_date) or pd.isna(end_date) or price == 0:
            return None
        if membership_type in five_day_memberships:
            duration_days = np.busday_count(
                start_date.date(), end_date.date() + timedelta(days=1)
            )
        else:
            duration_days = (end_date - start_date).days

        if duration_days <= 0:
            return None
        unit_price = price / duration_days
        return unit_price

    contracts_df["Unit Price (TL per day)"] = contracts_df.apply(
        calculate_unit_price, axis=1
    )
    # Kategorik kolonlar, yetersiz veri içerenleri "Others" yapma
    try:
        exclude_columns = ["Müşteri Kodu", "Sözleşme No"]
        categorical_columns = contracts_df.select_dtypes(include="object").columns
        categorical_columns = categorical_columns.difference(exclude_columns)

        category_mappings = {column: {} for column in categorical_columns}
        for column in categorical_columns:
            contingency_table = pd.crosstab(
                contracts_df[column], contracts_df["Yenileme Durumu"]
            )
            row_totals = contingency_table.sum(axis=1)
            column_totals = contingency_table.sum(axis=0)
            grand_total = contingency_table.values.sum()
            expected_frequencies = pd.DataFrame(
                [
                    [
                        (row_totals[row] * column_totals[col]) / grand_total
                        for col in contingency_table.columns
                    ]
                    for row in contingency_table.index
                ],
                index=contingency_table.index,
                columns=contingency_table.columns,
            )
            low_frequency_categories = (
                expected_frequencies[expected_frequencies < 5].dropna(how="all").index
            )
            if not low_frequency_categories.empty:
                category_mappings[column].update(
                    {category: "Others" for category in low_frequency_categories}
                )

        for column, mapping in category_mappings.items():
            if mapping:
                contracts_df[column] = contracts_df[column].replace(mapping)

        for column in categorical_columns:
            print(f"Counts for {column}:")
            print(contracts_df[column].value_counts())

    except Exception as e:
        print(f"An error occurred: {e}")

    # Saf Sözleşme - Asil No bulma
    def extract_pure_code(code):
        if isinstance(code, str):
            return code.split("-")[0]
        else:
            return code

    contracts_df["Sözleşme No"] = (
        contracts_df["Sözleşme No"].astype(str).replace("nan", "")
    )

    contracts_df["Pure Sözleşme No"] = contracts_df["Sözleşme No"].apply(
        extract_pure_code
    )

    # Aile üyeliklerinde ücret bölme
    def distribute_tutar(group):
        asil_member = group[group["Üyelik Tipi"] == "Asil Üyelik"]
        if not asil_member.empty:
            total_tutar = asil_member.iloc[0]["Unit Price (TL per day)"]
            member_count = len(group)
            distributed_tutar = total_tutar / member_count if member_count > 0 else 0
            group["Unit Price (TL per day)"] = distributed_tutar
        return group

    contracts_df = contracts_df.groupby("Pure Sözleşme No", group_keys=False).apply(
        distribute_tutar
    )
    contracts_df = contracts_df.drop(columns=["Pure Sözleşme No"])

    test_db = contracts_df.copy()

    # Yenileme Durumu NA olanlar
    filtered_db = test_db.dropna(subset=["Yenileme Durumu"])

    # Yenileme Oranı Bulma
    renewal_percentage = (
        filtered_db.groupby("Müşteri Kodu")["Yenileme Durumu"].mean() * 100
    )
    test_db["Renewal Percentage"] = test_db["Müşteri Kodu"].map(renewal_percentage)
    renewal_counts = test_db.groupby("Müşteri Kodu")["Yenileme Durumu"].sum()
    test_db["Number of Past Renewals"] = test_db["Müşteri Kodu"].map(renewal_counts)

    # Kategorilere Ayırma
    def assign_range_column(df, column, num_ranges=None, custom_ranges=None):
        try:
            if custom_ranges:
                bins = pd.cut(df[column], bins=custom_ranges, include_lowest=True)
                range_labels = [
                    f"[{custom_ranges[i]:.2f}-{custom_ranges[i + 1]:.2f})"
                    for i in range(len(custom_ranges) - 1)
                ]

                range_column_name = f"{column}_Range"
                df[range_column_name] = pd.cut(
                    df[column],
                    bins=custom_ranges,
                    labels=range_labels,
                    include_lowest=True,
                )
            else:
                bins, bin_edges = pd.qcut(
                    df[column], q=num_ranges, retbins=True, duplicates="drop"
                )
                range_labels = [
                    f"[{bin_edges[i]:.2f}-{bin_edges[i + 1]:.2f})"
                    for i in range(len(bin_edges) - 1)
                ]

                range_column_name = f"{column}_Range"
                df[range_column_name] = pd.qcut(
                    df[column], q=num_ranges, labels=range_labels, duplicates="drop"
                )
        except Exception as e:
            print(f"Error processing column '{column}': {e}")

        return df

    columns_to_divide = [
        "Sözleşme Yaşı",
        "Aranma Sayısı",
        "Overall Usage Percentage (%)",
        "Last 30 Days Utilization (%)",
        "Average_Visit_Duration",
        "Unit Price (TL per day)",
        "Renewal Percentage",
        "Number of Past Renewals",
    ]
    num_ranges = 7

    for column in columns_to_divide:
        if column == "Last 30 Days Utilization (%)":
            custom_bins = [0, 1, 30, 100]
            test_db = assign_range_column(test_db, column, custom_ranges=custom_bins)
        else:
            test_db = assign_range_column(test_db, column, num_ranges=num_ranges)

    print(f"Total number of rows after transformations: {test_db.shape[0]}")
    test_db.to_excel(os.path.join(output_dir, "test_db.xlsx"), sheet_name="a")

    # Rangeler oluştuktan sonra düşürülecek kolonlar
    columns_to_drop = [
        "Total Usage",
        "Last 30 Days Usage Count",
        "Sözleşme Yaşı",
        "Aranma Sayısı",
        "Overall Usage Percentage (%)",
        "Last 30 Days Utilization (%)",
        "Average_Visit_Duration",
        "Adjusted Tutar",
        "Unit Price (TL per day)",
        "Tutar ( TL )",
        "Renewal Percentage",
        "Number of Past Renewals",
        "Söz. TürüSözleşme Durumu",
        "Sözleşme Detay Durumu",
        "Ek Süreli Bitiş T.",
    ]
    testt_db = test_db.drop(columns=columns_to_drop, errors="ignore")

    # Show cleaned data
    print(
        f"Data shape after cleaning: {testt_db.shape[0]} rows, {testt_db.shape[1]} columns"
    )
    print(testt_db.columns.tolist())

    # Export test_db (original) if you want
    output_path = os.path.join(output_dir, "TESTE_HAZIRLIK_ONCESI_SON.xlsx")
    testt_db.to_excel(output_path, index=False)

    # LOGISTIC REGRESSION - sine eren

    # PARAMETERS
    train_ratio = 0.80
    sort_column = "Başlangıç T."
    target_col = "Yenileme Durumu"

    # STEP 1: Preprocessing
    # Safely drop unnecessary columns
    testt_db = testt_db.drop(
        columns=["Unnamed: 0", "Müşteri Kodu", "Sözleşme No"], errors="ignore"
    )

    # Drop rows with missing target or key columns
    testt_db = testt_db.dropna(subset=[target_col, "Üyelik Adı", sort_column])

    # Sort by date (important for time-based split)
    testt_db = testt_db.sort_values(by=sort_column).reset_index(drop=True)

    # STEP 2: Target & Feature Separation
    y = testt_db[target_col].astype(int)
    X = testt_db.drop(columns=[target_col])

    X = X.drop(columns=["Başlangıç T."], errors="ignore")
    X = X.astype(str)
    # STEP 3: Meaningful Base Category Selection
    base_profile = {}
    all_renewal_tables = {}

    for col in X.columns:
        temp = testt_db[[col, target_col]].dropna()
        stats = temp.groupby(col)[target_col].agg(["count", "mean"])
        stats.columns = ["sample_size", "renewal_rate"]
        stats = stats.sort_values(by="sample_size", ascending=False)
        all_renewal_tables[col] = stats

        median_renewal = stats["renewal_rate"].median()
        closest_to_median = stats.iloc[
            (stats["renewal_rate"] - median_renewal).abs().argsort()
        ].index[0]

        if stats.loc[closest_to_median, "sample_size"] >= 500:
            base_profile[col] = closest_to_median
        else:
            base_profile[col] = stats.index[0]

    # STEP 4: One-Hot Encoder with Custom Base Categories
    categories = []

    for feature in X.columns:
        base = str(base_profile[feature])  # force base to string
        others = [
            str(cat) for cat in all_renewal_tables[feature].index if str(cat) != base
        ]
        full_list = [base] + others
        categories.append(full_list)

    encoder = OneHotEncoder(
        categories=categories,
        drop="first",
        sparse_output=False,  # for sklearn >=1.2
        handle_unknown="ignore",
    )

    encoder = OneHotEncoder(
        categories=categories,
        drop="first",
        sparse_output=False,  # Correct for scikit-learn >= 1.2
        handle_unknown="ignore",
    )
    print("\nSelected Base Categories (Base Customer Profile):")
    for feature, base_value in base_profile.items():
        print(f"{feature}: {base_value}")

    # Store base profile into a DataFrame
    base_profile_df = pd.DataFrame(
        list(base_profile.items()), columns=["Feature", "Base_Category"]
    )

    # Save it to Excel
    base_profile_df.to_excel(r"processed/base_profile.xlsx", index=False)
    base_profile_df.to_excel(os.path.join(FIXED_DIR, "base_profile.xlsx"), index=False)

    print("\nBase profile has been exported to 'processed/base_profile.xlsx'.")

    # STEP 5: Train-Test Split (Time-Based)
    split_index = int(len(X) * train_ratio)
    X_train_raw, X_test_raw = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]

    # Drop any remaining NaNs
    train_df = pd.concat([X_train_raw, y_train], axis=1).dropna()
    testt_df = pd.concat([X_test_raw, y_test], axis=1).dropna()

    X_train = train_df.drop(columns=target_col)
    y_train = train_df[target_col]
    X_test = testt_df.drop(columns=target_col)
    y_test = testt_df[target_col]

    # STEP 6: Encode Features
    X_train_encoded = encoder.fit_transform(X_train)
    X_test_encoded = encoder.transform(X_test)

    encoded_columns = encoder.get_feature_names_out(X_train.columns)

    X_train_df = pd.DataFrame(X_train_encoded, columns=encoded_columns)
    X_test_df = pd.DataFrame(X_test_encoded, columns=encoded_columns)

    # STEP 7: Train Logistic Regression Model
    log_model = LogisticRegression(random_state=42, max_iter=1000)
    log_model.fit(X_train_df, y_train)

    # STEP 8: Prediction & Evaluation
    y_pred = log_model.predict(X_test_df)
    y_prob = log_model.predict_proba(X_test_df)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    conf_matrix = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred)

    # STEP 9: Outputs
    print(
        f"\nZamana Dayalı Bölünme ile Model Performansı (Eğitim Oranı: {train_ratio * 100:.0f}%)"
    )
    print("Accuracy:", accuracy)
    print("Confusion Matrix:\n", conf_matrix)
    print("Classification Report:\n", report)
    print("Intercept (β₀):", log_model.intercept_[0])

    # Correct coefficient extraction
    coefficients_df = pd.DataFrame(
        log_model.coef_[0], index=encoded_columns, columns=["Coefficients"]
    )

    # Optional: View top positive and negative coefficients
    print("\nTop Positive Influences on Renewal:")
    print(coefficients_df.sort_values(by="Coefficients", ascending=False).head(10))

    print("\nTop Negative Influences on Renewal:")
    print(coefficients_df.sort_values(by="Coefficients", ascending=True).head(10))

    # Opsiyonel: Temel müşteri için yenileme olasılığı
    p_baseline = 1 / (1 + np.exp(-log_model.intercept_[0]))
    print("📈 Basis customer'ın yenileme olasılığı: {:.3f}".format(p_baseline))

    # Export to Excel
    coefficients_df.to_excel(
        os.path.join(output_dir, "logistic_regression_coefficients.xlsx"),
        sheet_name="Coefficients",
    )

    print("Coefficients have been exported to 'logistic_regression_coefficients.xlsx'.")

    # Load the logistic regression coefficients Excel file
    coefficients_file_path = os.path.join(
        output_dir, "logistic_regression_coefficients.xlsx"
    )
    coefficients_df = pd.read_excel(coefficients_file_path)

    # Load the customer data Excel file
    customer_file_path = os.path.join(output_dir, "test_db.xlsx")
    customer_df = pd.read_excel(customer_file_path)

    # Rename the column for coefficients (keep Feature as column, do NOT set it as index)
    coefficients_df.columns = ["Feature", "Coefficient"]

    # Define the relevant categorical columns
    selected_columns = [
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

    # Create a copy of customer data for processing
    customer_scores = customer_df[["Sözleşme No"] + selected_columns].copy()

    # Initialize score with intercept
    intercept = log_model.intercept_[0]
    customer_scores["Score"] = intercept

    # Compute Score without using index
    for feature in selected_columns:
        for i, row in customer_scores.iterrows():
            feature_category = f"{feature}_{row[feature]}"
            matched_row = coefficients_df[
                coefficients_df["Feature"] == feature_category
            ]
            if not matched_row.empty:
                customer_scores.at[i, "Score"] += matched_row["Coefficient"].values[0]

    # Compute Probability
    customer_scores["Probability"] = 1 / (1 + np.exp(-customer_scores["Score"]))

    # Define thresholds
    thresholds = [0.5]

    # Assign Class for each threshold
    for threshold in thresholds:
        class_column = f"Class_{threshold}"
        customer_scores[class_column] = customer_scores["Probability"].apply(
            lambda x: 1 if x >= threshold else 0
        )

    # Sort by Probability
    output_df = customer_scores.sort_values(by="Probability", ascending=False)

    # Save results
    output_file = os.path.join(output_dir, "customer_probabilities_and_classes.xlsx")
    output_df.to_excel(output_file, index=False)

    print(f"Results with probabilities and class thresholds saved to {output_file}")
