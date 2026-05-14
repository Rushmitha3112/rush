"""
IEX India DAM Data Downloader — 2015 to 2022
=============================================
Run this script once to download all historical Day-Ahead Market data.
Output: data/iex/iex_dam_YYYY_MM.csv  (one file per month)

Usage:
    python download_iex_data.py

The IEX India website publishes monthly DAM market snapshots at:
    https://www.iexindia.com/Uploads/Market-Snapshot/

If the automated download fails (IEX changes the URL structure),
follow the manual instructions printed at the end of this script.
"""

import os
import time
import requests
from pathlib import Path
from datetime import date

OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "iex"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.iexindia.com/marketdata/dam/dammcpvolume.aspx",
})

# IEX has used these URL patterns historically — try each in order
URL_PATTERNS = [
    # Pattern 1: direct CSV by month
    "https://www.iexindia.com/Uploads/Market-Snapshot/DAM-MCP-Volume-{year}-{month:02d}.xlsx",
    # Pattern 2: alternate naming
    "https://www.iexindia.com/Uploads/Market-Snapshot/DAM_{year}{month:02d}.xlsx",
    # Pattern 3: CSV variant
    "https://www.iexindia.com/Uploads/MarketSnapshot/DAM-{year}-{month:02d}.csv",
]


def try_download(year: int, month: int) -> bool:
    """Try each URL pattern and save the file if successful."""
    out_path_xlsx = OUTPUT_DIR / f"iex_dam_{year}_{month:02d}.xlsx"
    out_path_csv  = OUTPUT_DIR / f"iex_dam_{year}_{month:02d}.csv"

    # skip if already downloaded
    if out_path_xlsx.exists() or out_path_csv.exists():
        print(f"  [{year}-{month:02d}] already downloaded, skipping")
        return True

    for pattern in URL_PATTERNS:
        url = pattern.format(year=year, month=month)
        try:
            resp = SESSION.get(url, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 1000:
                ext = ".xlsx" if "xlsx" in url else ".csv"
                out_path = OUTPUT_DIR / f"iex_dam_{year}_{month:02d}{ext}"
                out_path.write_bytes(resp.content)
                print(f"  [{year}-{month:02d}] Downloaded → {out_path.name}  ({len(resp.content)//1024} KB)")
                return True
        except requests.RequestException:
            continue

    print(f"  [{year}-{month:02d}] Not found via automated download")
    return False


def main():
    print("IEX India DAM Data Download — 2015 to 2022")
    print(f"Saving to: {OUTPUT_DIR}\n")

    failed = []
    for year in range(2015, 2023):
        print(f"Year {year}:")
        for month in range(1, 13):
            # don't request future months
            if date(year, month, 1) > date.today():
                break
            success = try_download(year, month)
            if not success:
                failed.append((year, month))
            time.sleep(0.5)  # be polite to the server

    print(f"\nDownload complete. {len(failed)} months could not be fetched automatically.")

    if failed:
        print("\n" + "="*60)
        print("MANUAL DOWNLOAD INSTRUCTIONS")
        print("="*60)
        print("For months that failed, download manually:")
        print("1. Go to: https://www.iexindia.com/marketdata/dam/dammcpvolume.aspx")
        print("2. Select the year and month from the dropdowns")
        print("3. Click 'Download' / 'Export'")
        print(f"4. Save files to: {OUTPUT_DIR}")
        print("5. Name them: iex_dam_YYYY_MM.xlsx  (e.g. iex_dam_2021_03.xlsx)")
        print("\nFailed months:")
        for y, m in failed:
            print(f"  {y}-{m:02d}")


if __name__ == "__main__":
    main()
