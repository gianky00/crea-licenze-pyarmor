import sqlite3
import datetime

class Database:
    """
    Classe per la gestione del database SQLite per il gestore di licenze.
    """
    def __init__(self, db_name="gestionale_licenze.db"):
        """
        Inizializza la connessione al database e crea le tabelle se non esistono.
        """
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """
        Crea le tabelle 'utenti' e 'storico_licenze' se non sono già presenti.
        """
        # Tabella per memorizzare i profili utente
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS utenti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_utente TEXT NOT NULL UNIQUE,
                hwid_scheda_madre TEXT NOT NULL,
                percorso_destinazione TEXT
            )
        """)
        try:
            self.cursor.execute("ALTER TABLE utenti ADD COLUMN percorso_destinazione TEXT;")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass # La colonna esiste già

        # Tabella per lo storico delle licenze generate
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS storico_licenze (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_utente INTEGER NOT NULL,
                data_scadenza TEXT NOT NULL,
                data_generazione TEXT NOT NULL,
                FOREIGN KEY (id_utente) REFERENCES utenti (id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    # --- Metodi per la gestione degli Utenti (CRUD) ---

    def add_user(self, nome_utente, hwid_scheda_madre, percorso_destinazione=None):
        """Aggiunge un nuovo utente nel database."""
        try:
            self.cursor.execute("INSERT INTO utenti (nome_utente, hwid_scheda_madre, percorso_destinazione) VALUES (?, ?, ?)", (nome_utente, hwid_scheda_madre, percorso_destinazione))
            self.conn.commit()
            return True, "Utente aggiunto con successo."
        except sqlite3.IntegrityError:
            return False, "Errore: Il nome utente esiste già."
        except Exception as e:
            return False, f"Errore sconosciuto: {e}"

    def get_all_users(self):
        """Restituisce tutti gli utenti dal database, ordinati per nome."""
        self.cursor.execute("SELECT id, nome_utente, hwid_scheda_madre, percorso_destinazione FROM utenti ORDER BY nome_utente")
        return self.cursor.fetchall()

    def update_user(self, user_id, new_nome_utente, new_hwid, new_percorso_destinazione):
        """Aggiorna i dati di un utente esistente."""
        try:
            self.cursor.execute("UPDATE utenti SET nome_utente = ?, hwid_scheda_madre = ?, percorso_destinazione = ? WHERE id = ?", (new_nome_utente, new_hwid, new_percorso_destinazione, user_id))
            self.conn.commit()
            return True, "Utente aggiornato con successo."
        except sqlite3.IntegrityError:
            return False, "Errore: Il nuovo nome utente esiste già."
        except Exception as e:
            return False, f"Errore sconosciuto: {e}"

    def delete_user(self, user_id):
        """Elimina un utente dal database."""
        try:
            self.cursor.execute("DELETE FROM utenti WHERE id = ?", (user_id,))
            self.conn.commit()
            return True, "Utente eliminato con successo."
        except Exception as e:
            return False, f"Errore sconosciuto: {e}"

    # --- Metodi per la gestione dello Storico Licenze ---

    def add_license_record(self, user_id, data_scadenza):
        """
        Aggiunge un record di una licenza generata allo storico.
        La data di generazione viene creata automaticamente.
        """
        try:
            data_generazione = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("INSERT INTO storico_licenze (id_utente, data_scadenza, data_generazione) VALUES (?, ?, ?)", (user_id, data_scadenza, data_generazione))
            self.conn.commit()
            return True, "Licenza registrata nello storico."
        except Exception as e:
            return False, f"Errore durante la registrazione della licenza: {e}"

    def get_license_history(self):
        """
        Restituisce lo storico completo delle licenze, unendo i dati degli utenti.
        I risultati sono ordinati dalla data di generazione più recente.
        """
        self.cursor.execute("""
            SELECT
                sl.id,
                u.nome_utente,
                sl.data_scadenza,
                sl.data_generazione
            FROM storico_licenze sl
            JOIN utenti u ON sl.id_utente = u.id
            ORDER BY sl.data_generazione DESC
        """)
        return self.cursor.fetchall()

    def get_license_history_by_user(self, user_id):
        """
        Restituisce lo storico delle licenze per un utente specifico.
        """
        self.cursor.execute("""
            SELECT
                sl.id,
                u.nome_utente,
                sl.data_scadenza,
                sl.data_generazione
            FROM storico_licenze sl
            JOIN utenti u ON sl.id_utente = u.id
            WHERE sl.id_utente = ?
            ORDER BY sl.data_generazione DESC
        """, (user_id,))
        return self.cursor.fetchall()

    def delete_license_record(self, license_id):
        """Elimina un record di licenza dallo storico."""
        try:
            self.cursor.execute("DELETE FROM storico_licenze WHERE id = ?", (license_id,))
            self.conn.commit()
            return True, "Record di licenza eliminato con successo."
        except Exception as e:
            return False, f"Errore sconosciuto: {e}"

    def close(self):
        """Chiude la connessione al database."""
        if self.conn:
            self.conn.close()

if __name__ == '__main__':
    # Esempio di utilizzo e test delle funzionalità
    db = Database()
    print("Database e tabelle create.")
    db.close()
    print("\nConnessione chiusa.")