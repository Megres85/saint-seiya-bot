import sqlite3
import pandas as pd
import discord
from discord import app_commands
from discord.ext import commands

# ==========================================
# CONFIGURAZIONE FILE E DATABASE
# ==========================================
EXCEL_FILE = "saint_seiya_database.xlsx"  # Sostituisci col nome del tuo file Excel
DB_FILE = "saint_seiya_db.sqlite"

def genera_database_da_excel():
    """Converte automaticamente ogni foglio dell'Excel in una tabella SQLite"""
    try:
        excel_data = pd.read_excel(EXCEL_FILE, sheet_name=None)
        conn = sqlite3.connect(DB_FILE)
        for sheet_name, df in excel_data.items():
            table_name = sheet_name.strip().lower().replace(" ", "_").replace("&", "e")
            df.to_sql(table_name, conn, if_exists='replace', index=False)
        conn.close()
        print("Database SQLite aggiornato con successo dall'Excel!")
    except Exception as e:
        print(f"Errore durante la conversione dell'Excel: {e}")

genera_database_da_excel()

# ==========================================
# SETUP BOT
# ==========================================
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot online come {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizzati {len(synced)} comandi Slash.")
    except Exception as e:
        print(f"Errore di sincronizzazione: {e}")

# ==========================================
# SISTEMA DI PAGINAZIONE CON PULSANTI
# ==========================================
class DatabasePaginationView(discord.ui.View):
    def __init__(self, risultati, colonne, tabella, termine):
        super().__init__(timeout=180) # Il menu scade dopo 3 minuti di inattività
        self.risultati = risultati
        self.colonne = colonne
        self.tabella = tabella
        self.termine = termine
        self.page = 0
        self.max_pages = len(risultati)
        self.update_buttons()

    def update_buttons(self):
        # Abilita o disabilita i pulsanti in base alla pagina corrente
        self.prev_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= self.max_pages - 1

    def build_embed(self):
        riga = self.risultati[self.page]
        embed = discord.Embed(
            title=f"🔍 Risultato {self.page + 1} di {self.max_pages} ({self.tabella})",
            description=f"Ricerca per: **{self.termine}**",
            color=discord.Color.from_rgb(212, 175, 55) # Tema dorato Saint Seiya
        )
        
        # Popola i campi dell'embed con i dati della riga
        for col, val in zip(self.colonne, riga):
            if val is not None and str(val).strip() != "":
                embed.add_field(name=col.replace("_", " ").title(), value=str(val), inline=False)
                
        return embed

    @discord.ui.button(label="◀ Precedente", style=discord.ButtonStyle.secondary, disabled=True)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Successivo ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.max_pages - 1:
            self.page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

# ==========================================
# COMANDO SLASH CON AUTOCOMPLETE
# ==========================================

# Funzione di supporto per suggerire le tabelle in base al database
async def tabella_autocomplete(interaction: discord.Interaction, current: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelle = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Filtra i suggerimenti in base a ciò che l'utente sta scrivendo
    return [
        app_commands.Choice(name=t.replace("_", " ").title(), value=t)
        for t in tabelle if current.lower() in t.lower()
    ][:25]

@bot.tree.command(name="cerca", description="Cerca informazioni nel database del gioco con filtri")
@app_commands.describe(
    tabella="Seleziona la categoria (foglio Excel)",
    termine="Cosa vuoi cercare (es. Shura, Stun, Attacco)",
    filtro_colonna="Opzionale: Nome di una colonna specifica in cui cercare"
)
@app_commands.autocomplete(tabella=tabella_autocomplete)
async def cerca(interaction: discord.Interaction, tabella: str, termine: str, filtro_colonna: str = None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    tabella_pulita = tabella.strip().lower()
    
    try:
        # Verifica esistenza tabella
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabella_pulita,))
        if not cursor.fetchone():
            await interaction.response.send_message(f"⚠️ La categoria **{tabella}** non esiste.", ephemeral=True)
            conn.close()
            return

        # Estrae le colonne della tabella
        cursor.execute(f"PRAGMA table_info({tabella_pulita})")
        colonne = [info[1] for info in cursor.fetchall()]
        
        # Costruisce la query di ricerca
        if filtro_colonna and filtro_colonna in colonne:
            query = f"SELECT * FROM {tabella_pulita} WHERE {filtro_colonna} LIKE ?"
            cursor.execute(query, (f"%{termine}%",))
        else:
            condizioni = " OR ".join([f"{col} LIKE ?" for col in colonne])
            valori_query = [f"%{termine}%" for _ in colonne]
            query = f"SELECT * FROM {tabella_pulita} WHERE {condizioni}"
            cursor.execute(query, valori_query)
            
        risultati = cursor.fetchall()
        
        if not risultati:
            await interaction.response.send_message(f"Nessun risultato trovato per **{termine}** nella categoria **{tabella}**.", ephemeral=True)
            conn.close()
            return

        # Avvia la vista con paginazione se ci sono risultati
        view = DatabasePaginationView(risultati, colonne, tabella, termine)
        await interaction.response.send_message(embed=view.build_embed(), view=view)
        
    except Exception as e:
        await interaction.response.send_message(f"Errore durante la ricerca: {e}", ephemeral=True)
    finally:
        conn.close()

bot.run("IL_TUO_TOKEN_DISCORD")
