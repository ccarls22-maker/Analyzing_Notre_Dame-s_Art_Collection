

import pandas as pd

file_path = "cleaned_date_and_special_characters.csv"
df = pd.read_csv(file_path)


continent_map = {
    "Africa": "Africa",
    "North America": "North America",
    "South America": "South America",
    "Europe": "Europe",
    "Asia": "Asia",
    "Oceania": "Oceania",
    "Australia": "Oceania",   # sometimes appears separately
    "Antarctica": "Antarctica"
}

def extract_continent(location):
    if pd.isna(location):
        return None
    for keyword, continent in continent_map.items():
        if keyword.lower() in location.lower():
            return continent
    return None

# Create the Continent column
df["Continent"] = df["related_location"].apply(extract_continent)

# Save quick result
output_path = "raclin_murphy_artworks_with_continents.csv"
df.to_csv(output_path, index=False)
print(f"✅ File saved to {output_path}")

dfcontinents = pd.read_csv("raclin_murphy_artworks_with_continents.csv")
dfcontinents.head()

