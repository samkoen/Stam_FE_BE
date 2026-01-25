# Emplacement du fichier .env

## 📍 Où créer le fichier `.env` ?

Le fichier `.env` doit être créé dans le dossier **`StamStam-BE/`**, au même niveau que :

- `config.py`
- `app.py`
- `ENV_EXAMPLE.txt`
- `gunicorn_config.py`
- `Procfile`

## 📂 Structure correcte

```
StamStam-BE/
├── .env                  ← ICI (même dossier que config.py)
├── config.py
├── app.py
├── ENV_EXAMPLE.txt
├── gunicorn_config.py
├── start_production.py
└── ...
```

## 🔧 Création du fichier .env

### Sur Windows (PowerShell)

```powershell
cd StamStam-BE
Copy-Item ENV_EXAMPLE.txt .env
```

### Sur Linux/Mac

```bash
cd StamStam-BE
cp ENV_EXAMPLE.txt .env
```

## ✅ Pourquoi dans StamStam-BE/ ?

Le fichier `config.py` utilise :
```python
BASE_DIR = Path(__file__).parent.absolute()
```

Cela signifie que `BASE_DIR` pointe vers le répertoire où se trouve `config.py`, c'est-à-dire `StamStam-BE/`.

Donc le fichier `.env` doit être dans `StamStam-BE/` pour que :
- `config.py` puisse le trouver facilement
- Les chemins relatifs fonctionnent correctement
- La structure reste claire et organisée

## ⚠️ Important

- Le fichier `.env` est dans `.gitignore` (ne sera pas commité)
- Modifiez `.env` selon vos besoins (ne modifiez pas `ENV_EXAMPLE.txt`)
- En production, configurez les variables d'environnement directement sur le serveur ou via systemd/supervisor

