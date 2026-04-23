import re
import time
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


URL = "https://www.uhaul.com/About/Migration/"

YEARS = [str(y) for y in range(2010, 2024)]

STATES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}


def extract_field(text: str, label: str) -> str | None:
    """
    Extract the line immediately after a label like 'In-migration:'.
    """
    pattern = rf"{re.escape(label)}\s*\n([^\n]+)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def parse_percent(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.replace("%", "").strip()
    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    value = re.sub(r"[^\d]", "", value)
    try:
        return int(value)
    except ValueError:
        return None


def scrape_one(driver, wait, year: str, state_abbr: str, state_name: str) -> dict:
    driver.get(URL)

    year_elem = wait.until(EC.presence_of_element_located((By.ID, "usYear")))
    state_elem = wait.until(EC.presence_of_element_located((By.ID, "usState")))

    Select(year_elem).select_by_visible_text(year)
    Select(state_elem).select_by_visible_text(state_name)

    continue_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Continue')]"))
    )
    driver.execute_script("arguments[0].click();", continue_btn)


    wait.until(lambda d: state_name in d.find_element(By.TAG_NAME, "body").text)

    time.sleep(2)
    body_text = driver.find_element(By.TAG_NAME, "body").text

    growth_rank = parse_int(extract_field(body_text, "Growth State Rank:"))
    in_migration = parse_percent(extract_field(body_text, "In-migration:"))
    out_migration = parse_percent(extract_field(body_text, "Out-migration:"))
    leading_cities = extract_field(body_text, "Leading U.S. Growth Cities:")

    return {
        "year": int(year),
        "state": state_name,
        "state_abbr": state_abbr,
        "growth_rank": growth_rank,
        "in_migration_pct": in_migration,
        "out_migration_pct": out_migration,
        "leading_cities": leading_cities,
    }


def main():
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    wait = WebDriverWait(driver, 20)

    results = []
    failed = []

    try:
        for year in YEARS:
            for abbr, state_name in STATES.items():
                print(f"Scraping {year} - {state_name}")
                try:
                    row = scrape_one(driver, wait, year, abbr, state_name)
                    results.append(row)
                    time.sleep(1)
                except Exception as e:
                    print(f"FAILED: {year} - {state_name} -> {e}")
                    failed.append(
                        {
                            "year": year,
                            "state": state_name,
                            "state_abbr": abbr,
                            "error": str(e),
                        }
                    )

        df = pd.DataFrame(results)
        df["net_migration_pct"] = df["in_migration_pct"] - df["out_migration_pct"]

        df.to_csv("uhaul_migration_2010_2023.csv", index=False)
        print(f"\nSaved {len(df)} rows to uhaul_migration_2010_2023.csv")

        if failed:
            fail_df = pd.DataFrame(failed)
            fail_df.to_csv("uhaul_scrape_failures.csv", index=False)
            print(f"Saved {len(failed)} failed rows to uhaul_scrape_failures.csv")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()