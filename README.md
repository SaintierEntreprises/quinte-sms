# Quinté du jour par SMS (0 €)

Chaque matin, GitHub (gratuit) récupère deux choses et les écrit dans `quinte.txt` :
- le pronostic Quinté+ d'Equidia ;
- la synthèse de la presse : les ~30 journaux recensés par turf-fr.com, fusionnés en un classement où la 1re place vaut 8 points et la 8e vaut 1 point.

À 10 h, un raccourci sur ton iPhone lit ce fichier et l'envoie par SMS à ton grand-père.

Exemple de SMS (un seul SMS, lignes courtes pour un petit écran) :

```
QUINTE 15/11 15H15
AUTEUIL
EQUIDIA
13 4 9 12
11 8 1 15
PRESSE
4 1 7 12
3 13 11 8
```

Si la presse n'est pas disponible un matin, le SMS part quand même avec Equidia seul.
Si c'est Equidia qui manque, rien n'est envoyé à ton grand-père et c'est toi qui reçois une alerte.

## 1. Mettre le dépôt sur GitHub (10 min)

**Option A — avec Claude Code ou le terminal (le plus simple)**

```bash
cd quinte-sms
git init && git add . && git commit -m "init"
gh repo create quinte-sms --public --source . --push
```

**Option B — dans le navigateur**
1. github.com → New repository → nom `quinte-sms` → **Public** → Create.
2. « Add file » → « Upload files » → dépose `quinte.py`, `README.md` et le dossier `tests`.
3. « Add file » → « Create new file » → nom : `.github/workflows/quinte.yml` → colle le contenu du fichier `quinte.yml` → Commit.

Le dépôt doit être **public** : le raccourci lit le fichier sans mot de passe. Il ne contient aucune donnée perso.

## 2. Premier test (2 min)

1. Onglet **Actions** → « Pronostic Quinte du jour » → **Run workflow**.
2. Au bout d'environ 1 min, le job doit être vert, et `quinte.txt` doit apparaître à la racine du dépôt.
3. Ouvre `https://raw.githubusercontent.com/TON-PSEUDO/quinte-sms/main/quinte.txt` → tu dois voir le SMS.

Problèmes possibles :
- **Erreur au `git push` (403)** → Settings → Actions → General → Workflow permissions → « Read and write permissions ».
- **Job rouge avec « ERREUR … introuvable »** → normal si le Quinté du jour est déjà couru (l'après-midi, Equidia n'affiche plus que celui de demain). Relance un matin.
- **Job rouge avec « ERREUR … HTTP 403 »** → Equidia bloque les serveurs GitHub. Préviens-moi : on fera tourner le script ailleurs.

En cas d'échec, GitHub t'envoie un e-mail automatiquement.

## 3. Le raccourci iPhone (10 min)

App **Raccourcis** → onglet **Automatisation** → **+** → **Heure de la journée** → 10:00, **Tous les jours** → **Exécuter immédiatement** → Nouveau raccourci vide. Ajoute ces actions dans l'ordre :

1. **URL** : `https://raw.githubusercontent.com/TON-PSEUDO/quinte-sms/main/quinte.txt`
2. **Obtenir le contenu de l'URL**
3. **Obtenir le texte de l'entrée** (entrée = Contenu de l'URL)
4. **Date** (Date actuelle) → **Formater la date** : Format personnalisé `dd/MM`
5. **Si** *Texte* **contient** *Date formatée*
   - **Si** *Texte* **commence par** `QUINTE`
     - **Envoyer un message** : *Texte* → destinataire : Papi. Ouvre le détail de l'action et **décoche « Afficher lors de l'exécution »**.
   - **Sinon** → **Envoyer un message** « Quinté : problème, rien envoyé à Papi » → destinataire : toi
6. **Sinon** (le fichier n'est pas celui d'aujourd'hui) → **Envoyer un message** « Quinté : fichier pas à jour » → destinataire : toi

**Test** : mets d'abord **ton propre numéro** à la place de celui de Papi, puis fais ▶︎ sur le raccourci.

## 4. Mise en service

- Pendant 7 jours, compare le SMS reçu avec equidia.fr/pronostics.
- Si les 7 SMS sont corrects, remplace ton numéro par celui de ton grand-père.

## Limites à connaître

- **Téléphone éteint ou hors réseau à 10 h** → aucun SMS ce jour-là.
- **Changement de structure du site Equidia** → le script affiche ERREUR, tu reçois l'alerte, et il faut adapter `quinte.py` (environ 10 min avec Claude Code).
- **Changement de structure de turf-fr.com** → la ligne PRESSE disparaît du SMS. Dans l'onglet Actions, le log affiche « presse indisponible ».
- **Mise en veille par GitHub** : GitHub désactive les tâches planifiées d'un dépôt public sans activité pendant 60 jours. Le commit quotidien de `quinte.txt` devrait suffire à l'éviter. Si GitHub t'envoie un e-mail « scheduled workflow disabled », clique sur « Enable ».

## Test hors ligne

```bash
pip install beautifulsoup4
python tests/test_quinte.py
```
