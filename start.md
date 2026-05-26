# START — Cockpit Sparring Partner
> Claude Code CLI entry point

## Mode
YOLO MITL — no HITL during build.
Execute autonomously. Ne demande pas de confirmation. Si tu bloques sur un choix technique, prends la décision qui respecte les contraintes stack déclarées dans blueprint.md et continue.

## Instructions
1. Lis `blueprint2.md` en entier avant d'écrire une seule ligne de code
2. Lance `npx getshitdone` avec `blueprint.md` comme plan d'exécution
3. Exécute chaque étape dans l'ordre des dépendances déclaré dans blueprint.md
4. Après chaque composant : exécute le test d'acceptance correspondant (`## ACCEPTANCE TEST`)
5. Si un test échoue : corrige et relance le test. Ne passe pas à l'étape suivante tant que le test n'est pas vert
6. Si une dépendance externe est indisponible (API key absente etc.) : crée un mock fonctionnel et continue, log le mock dans `MOCKS.md`
7. À la fin : génère `DONE.md` avec la liste des composants buildés, les mocks actifs, et les commandes de démarrage

## Contraintes absolues
- Ne jamais hardcoder une API key
- Ne jamais bypasser le VRAI_SP node (entry point unique du graph)
- Ne jamais mélanger les mémoires de deux profiles_id distincts
- Stack = ce qui est dans blueprint.md, pas ce que tu connais par défaut

## Go.
