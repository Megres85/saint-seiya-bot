import pandas as pd
import re

FILE_EXCEL = "saint_seiya_database.xlsx"

def aggiorna_cella(valore):
    if not isinstance(valore, str):
        return valore
    
    # 1. Sostituisce Arcano con Segreta
    valore = re.sub(r'\bArcano\b', 'Segreta', valore)
    valore = re.sub(r'\barcano\b', 'segreta', valore)
    
    # 2. Mette a capo i livelli (Lv 2, Lv 3, ecc.)
    valore = re.sub(r'(?<!^)\s*(Lv\.?\s*2|Livello\s*2|Lvl\.?\s*2)', r'\n\1', valore, flags=re.IGNORECASE)
    valore = re.sub(r'(?<!^)\s*(Lv\.?\s*3|Livello\s*3|Lvl\.?\s*3)', r'\n\1', valore, flags=re.IGNORECASE)
    valore = re.sub(r'(?<!^)\s*(Lv\.?\s*4|Livello\s*4|Lvl\.?\s*4)', r'\n\1', valore, flags=re.IGNORECASE)
    
    return valore

print("Modifica di tutti i fogli dell'Excel in corso...")
xls = pd.ExcelFile(FILE_EXCEL)
fogli = {}

for sheet in xls.sheet_names:
    df = pd.read_excel(FILE_EXCEL, sheet_name=sheet)
    df = df.applymap(aggiorna_cella)
    fogli[sheet] = df

# Sovrascrive il file originale
with pd.ExcelWriter(FILE_EXCEL, engine='openpyxl') as writer:
    for sheet, df in fogli.items():
        df.to_excel(writer, sheet_name=sheet, index=False)

print("🎉 File Excel aggiornato e sovrascritto con successo!")
