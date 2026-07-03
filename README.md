# PortaSplit Watch 🌡️

Traqueur de stock **100% gratuit** pour le Midea PortaSplit, façon ClimRadar mais sans abonnement.
Scanne Amazon, Leroy Merlin, Boulanger, Darty et ManoMano toutes les 15 minutes via GitHub Actions,
t'envoie une alerte ntfy dès qu'un site repasse en stock, et affiche un dashboard en direct via GitHub Pages.

Coût : **0 €**. Pas de serveur à payer, pas de carte bancaire à donner nulle part.

---

## 1. Créer le dépôt GitHub

1. Va sur [github.com/new](https://github.com/new), crée un dépôt (public ou privé, les deux marchent),
   par exemple `portasplit-watch`.
2. Mets tous les fichiers de ce dossier dedans (glisser-déposer sur github.com fonctionne, ou via `git push`).

## 2. Choisir ton "topic" ntfy (30 secondes, gratuit, sans compte)

1. Installe l'app **ntfy** (par *Philipp Heckel*) sur ton téléphone — [App Store](https://apps.apple.com/us/app/ntfy/id1625396347) ou Google Play.
   ⚠️ Ne confonds pas avec "NTFY - See who's up" ou "Ntfy me", ce sont d'autres apps sans rapport.
2. Choisis un nom de topic **unique et pas devinable** (les topics sont publics — n'importe qui connaissant
   le nom peut y publier ou s'abonner). Par exemple : `portasplit-alerte-x7k2m`.
3. Dans l'app, appuie sur **"+"** → **Subscribe to topic** → tape ton nom de topic → **Subscribe**.
   C'est tout, pas de compte, pas de token à générer.

## 3. Ajouter le secret dans GitHub

Dans ton dépôt : **Settings → Secrets and variables → Actions → New repository secret**

- `NTFY_TOPIC` = le nom de topic choisi à l'étape 2.2 (ex: `portasplit-alerte-x7k2m`)

## 4. Activer GitHub Pages

**Settings → Pages → Source** → choisis `Deploy from a branch`, branche `main`, dossier `/ (root)`. Sauvegarde.
Ton dashboard sera visible sur `https://TON-PSEUDO.github.io/portasplit-watch/` après quelques minutes.

## 5. Lancer le premier scan

**Actions → Check PortaSplit stock → Run workflow** (bouton à droite). Ensuite il tournera tout seul toutes les 15 min.

---

## Fichiers

- `scraper.py` — le script qui vérifie chaque site et envoie l'alerte ntfy
- `.github/workflows/check-stock.yml` — le cron GitHub Actions (gratuit, illimité sur dépôt public ;
  2000 min/mois gratuites sur dépôt privé, largement suffisant ici)
- `index.html` — le dashboard, lit `status.json` et l'affiche
- `status.json` — généré/mis à jour automatiquement par le script, ne pas éditer à la main

## Limites à connaître

- **Amazon bloque souvent les requêtes automatisées** (403/captcha) depuis des IP de datacenter comme celles
  de GitHub Actions. Si Amazon reste marqué "Bloqué", ce n'est pas un bug — c'est attendu. Les 4 autres sites
  (Leroy Merlin, Boulanger, Darty, ManoMano) sont nettement plus fiables pour ce genre de scan.
- Si un site change la structure de sa page, la détection peut se dérégler. Dans ce cas, ouvre `scraper.py`
  et ajuste les `in_stock_markers` / `out_of_stock_markers` du site concerné en regardant le texte affiché
  sur sa page quand le produit est en rupture.
- Pense à espacer les vérifications (15 min minimum) : bombarder ces sites de requêtes trop fréquentes
  peut te faire bannir temporairement.

## Ajouter un autre site

Ouvre `scraper.py`, ajoute un bloc dans la liste `SITES` :

```python
{
    "name": "Nom de l'enseigne",
    "url": "https://...",
    "in_stock_markers": ["ajouter au panier"],
    "out_of_stock_markers": ["rupture de stock", "indisponible"],
},
```
