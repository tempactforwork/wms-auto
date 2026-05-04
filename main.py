import io
import os
import sys
import pandas as pd
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client

from scraper import ErpInventoryScraper

load_dotenv()

# 임시
UPLOAD_FILENAME = "inventory_latest.parquet"
DOWNLOAD_DIR = "./downloads"
KST = timezone(timedelta(hours=9))


def process(file_path: str) -> pd.DataFrame:
    df = pd.read_excel(file_path)
    df = df[["존코드", "품목코드", "품목명", "로트번호", "가용수량", "가용중량(Kg)", "소비기한", "잔여기간", "잔여율"]].copy()
    df = df[~df['존코드'].str.contains('SHP|DMG')].copy()
    df = df.groupby(['품목코드', '품목명', '로트번호']).agg({
            '가용수량':'sum',
            '가용중량(Kg)':'sum',
            '소비기한':'first',
            '잔여기간':'first',
            '잔여율':'first'
        }).reset_index()
    df["소비기한"] = pd.to_datetime(df["소비기한"], format="%Y.%m.%d", errors="coerce")
    df["최종 업데이트 일시"] = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    return df


def upload(df: pd.DataFrame) -> None:
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    bucket = os.getenv("SUPABASE_BUCKET")

    buf = io.BytesIO()
    df.to_parquet(buf, index=False)

    client.storage.from_(bucket).upload(
        UPLOAD_FILENAME,
        buf.getvalue(),
        {
            "content-type": "application/octet-stream",
            "upsert": "true",
        },
    )
    print(f"✅ Supabase 업로드 완료: {bucket}/{UPLOAD_FILENAME}")


def main() -> None:
    # Step 1: 다운로드
    scraper = ErpInventoryScraper(
        url=os.getenv("ERP_URL"),
        user_id=os.getenv("ERP_ID"),
        password=os.getenv("ERP_PASSWORD"),
    )
    file_path = scraper.download_excel(download_dir=DOWNLOAD_DIR)
    if not file_path:
        print("❌ 다운로드 실패 — 중단합니다.")
        sys.exit(1)

    # Step 2: 전처리
    df = process(file_path)
    print(f"✅ 전처리 완료: {len(df)}행")

    # Step 3: Supabase 업로드
    upload(df)


if __name__ == "__main__":
    main()
