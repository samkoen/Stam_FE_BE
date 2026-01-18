# Étapes indispensables pour déployer sur un serveur

## 🔴 CRITIQUE - À faire AVANT le déploiement

### 1. Variables d'environnement et Configuration ⚙️
**Statut : ⚠️ MANQUE**

**Pourquoi :** Les chemins hardcodés et les configurations en dur ne fonctionneront pas sur un serveur.

**À faire :**
- Créer un fichier `config.py` centralisé
- Utiliser des variables d'environnement pour :
  - Chemins des fichiers (modèle ML, parachot)
  - Mode debug/production
  - Ports et URLs
  - Logging

**Impact :** 🔴 CRITIQUE - L'application ne fonctionnera pas sans cela.

---

### 2. Serveur de production (Gunicorn/Uvicorn) 🚀
**Statut : ⚠️ MANQUE**

**Pourquoi :** `uvicorn` en mode dev n'est pas adapté pour la production.

**À faire :**
- Créer un `Procfile` ou script de démarrage pour FastAPI avec Gunicorn/Uvicorn
- Configurer les workers pour la production
- Ajouter timeout et autres paramètres de production

**Impact :** 🔴 CRITIQUE - L'application sera lente/instable sans serveur de production.

---

### 3. Health Check endpoint 🏥
**Statut : ⚠️ MANQUE**

**Pourquoi :** Pour vérifier que l'application fonctionne (monitoring, load balancer, etc.)

**À faire :**
- Ajouter un endpoint `/health` dans `app.py`
- Vérifier que le modèle ML peut être chargé
- Vérifier l'accès aux fichiers nécessaires

**Impact :** 🟡 IMPORTANT - Difficile de savoir si l'application fonctionne sans cela.

---

### 4. Configuration Production (Debug désactivé) 🔒
**Statut : ⚠️ À VÉRIFIER**

**Pourquoi :** Le mode debug expose des informations sensibles et est plus lent.

**À faire :**
- S'assurer que `debug=False` en production
- Désactiver les logs détaillés sauf si nécessaire
- Configurer les CORS correctement (pas `allow_origins=["*"]` en prod)

**Impact :** 🔴 CRITIQUE - Sécurité et performance.

---

### 5. Validation des fichiers uploadés 🛡️
**Statut : ⚠️ À VÉRIFIER**

**Pourquoi :** Sans validation, quelqu'un peut uploader n'importe quoi et faire planter le serveur.

**À faire :**
- Limiter la taille des fichiers (ex: max 10MB)
- Vérifier le format (uniquement images : jpg, png, etc.)
- Gérer les erreurs gracieusement

**Impact :** 🔴 CRITIQUE - Sécurité et stabilité.

---

## 🟡 IMPORTANT - À faire rapidement après

### 6. Documentation de déploiement 📚
**Statut : ⚠️ MANQUE**

**Pourquoi :** Sans documentation, difficile de déployer et maintenir.

**À faire :**
- Guide de déploiement pas à pas
- Liste des dépendances système
- Configuration du serveur (nginx, etc.)
- Variables d'environnement à configurer

**Impact :** 🟡 IMPORTANT - Facilite le déploiement et la maintenance.

---

### 7. Rate Limiting (limitation de requêtes) 🚦
**Statut : ⚠️ MANQUE**

**Pourquoi :** Sans limitation, quelqu'un peut surcharger le serveur.

**À faire :**
- Ajouter `slowapi` ou middleware de rate limiting
- Limiter à X requêtes par minute/IP
- Retourner des erreurs 429 (Too Many Requests)

**Impact :** 🟡 IMPORTANT - Protection contre les abus.

---

### 8. Configuration du serveur web (Nginx) 🌐
**Statut : ⚠️ À VÉRIFIER**

**Pourquoi :** Pour servir le frontend et faire du reverse proxy vers FastAPI.

**À faire :**
- Configuration Nginx pour servir le frontend buildé
- Reverse proxy vers FastAPI sur un port local
- HTTPS/SSL (Let's Encrypt)

**Impact :** 🟡 IMPORTANT - Nécessaire pour un déploiement complet.

---

## 🟢 OPTIONNEL - Peut attendre

### 9. Monitoring et Métriques
- Endpoint `/metrics` (Prometheus)
- Alertes automatiques
- Dashboard de monitoring

### 10. Base de données
- Seulement si vous voulez sauvegarder l'historique
- Pas nécessaire pour la fonctionnalité de base

### 11. CI/CD
- Tests automatiques avant déploiement
- Déploiement automatique
- Pas critique pour un premier déploiement

---

## 📋 Checklist de déploiement

### Avant le déploiement
- [ ] Variables d'environnement configurées
- [ ] `config.py` créé et utilisé
- [ ] Mode debug désactivé en production
- [ ] Serveur de production configuré (Gunicorn/Uvicorn)
- [ ] Health check endpoint `/health` créé
- [ ] Validation des fichiers uploadés (taille, format)
- [ ] CORS configuré correctement (pas `*` en prod)
- [ ] Logging configuré pour production (pas de fichier par défaut)

### Après le déploiement
- [ ] Rate limiting activé
- [ ] Nginx configuré (reverse proxy + frontend)
- [ ] HTTPS/SSL configuré
- [ ] Monitoring en place
- [ ] Documentation de déploiement complétée

---

## 🎯 Ordre de priorité recommandé

1. **Variables d'environnement** (config.py) - 1-2h
2. **Health check endpoint** - 30min
3. **Serveur de production** (Gunicorn) - 1h
4. **Validation fichiers** - 1h
5. **Configuration production** (debug=False, CORS) - 30min
6. **Documentation déploiement** - 2h
7. **Rate limiting** - 1h
8. **Nginx + HTTPS** - 2-3h

**Temps total estimé : 8-10 heures**

---

## 💡 Notes importantes

- **Ne pas déployer avec `debug=True`** en production
- **Ne pas utiliser `allow_origins=["*"]`** en production pour CORS
- **Toujours utiliser HTTPS** en production
- **Tester sur un environnement de staging** avant la production
- **Avoir un plan de rollback** si quelque chose ne fonctionne pas

---

*Dernière mise à jour : [Date]*
*Projet : StamStam - Déploiement Production*

