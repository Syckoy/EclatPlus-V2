# EclatPlus (Python)

Application Windows minimale pour augmenter l’éclat des couleurs.

**Priorité : performances > stabilité > fonction > interface.**

## Choix technique

Python 3.12 **embarqué**, bibliothèque standard uniquement (`ctypes`). Pas de Tk, pas de pip.

Pourquoi Python ici, et pas C++ / .NET :

- Le travail utile n’est pas du traitement d’image en Python. C’est **un appel driver** (NVIDIA/AMD) au moment où tu bouges le curseur.
- Au repos, la fenêtre Win32 attend un message (`GetMessage`). **Pas de boucle, pas de timer, pas de capture d’écran.**
- .NET 8 WinForms charge un runtime lourd et l’ancienne appli laissait la **Loupe Windows** active trop tôt (dès 50), ce qui coûte des FPS.
- C++ serait un peu plus léger en RAM, mais le CPU au repos serait le même. Tu as demandé Python : le goulot, c’est la Loupe, pas l’interpréteur.

Dépendances : **aucune** (`pip` vide). Windows 10/11 64 bits, NVIDIA ou AMD.

## Architecture

```
curseur 0–200
    │
    ├─ 0–100  → NVAPI Digital Vibrance  ou  ADL Saturation
    │            (un appel, seulement si la valeur change)
    │
    └─ 101–200 + « Limiter au pilote » décoché
                 → MagSetFullscreenColorEffect une fois
                 → MagUninitialize dès que tu redescends ≤ 100 ou que tu limites
```

- **50** = rendu normal du pilote  
- **0** = saturation mini du pilote  
- **100** = max officiel NVIDIA/AMD  
- **> 100** = saturation extra (matrice 5×5, teinte inchangée, gris moyen 1/3)  
- **Limiter au pilote** : jamais de Loupe, plafond 100  

Pas d’injection, pas de ReShade, pas de screenshot, pas de thread de traitement.

## GitHub / personnes sans Python

Double-clic sur **`lancer.bat`**.

- Si Python 3.12+ 64 bits est **déjà installé** : l’appli se lance. Rien n’est téléchargé.
- S’il n’y est pas : une question **Oui / Non**. Non = pas d’appli. Oui = installe uniquement Python 3.12, puis lance.

## Fichiers

| Fichier | Rôle |
|---|---|
| `lancer.bat` | lance l’appli ; propose Python seulement s’il manque |
| `eclatplus.py` | tout le logiciel |
| `build_exe.bat` | fabrique `dist\EclatPlus.exe` |
| `settings.json` | `%AppData%\EclatPlus\` (écrit à la fermeture ou sur case à cocher) |

## Lancer

```bat
lancer.bat
```

`--tray` : démarre minimisé.  
`--selftest` : `python eclatplus.py --selftest`

## Créer le .exe

Le `.exe` PyInstaller embarque Python : plus pratique, **plus de RAM** que `pythonw`. Pour jouer, préfère `pythonw`.

```bat
build_exe.bat
```

Sortie : `dist\EclatPlus.exe`

À la main :

```bat
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --noconsole --name EclatPlus eclatplus.py
```

## Mises à jour

Au lancement, EclatPlus lit `version.json` sur le dépôt  
https://github.com/Syckoy/EclatPlus-V2  
(branche `main`, pas les Releases). Si le numéro est plus haut, il propose d’installer le zip du repo. Les réglages `%AppData%` restent.

Pour publier une version : augmente `version` dans `version.json` **et** `LOCAL_VERSION` dans `eclatplus.py`, puis pousse sur `main`.

## Fermeture

**Quitter** restaure le Digital Vibrance / la saturation d’origine et coupe la Loupe.  
Un `atexit` fait la même chose si le process se termine normalement.  
`TerminateProcess` (Fin de tâche brutal) peut laisser le réglage **pilote** tel quel : la vibrance GPU survit au process. Relancer et cliquer **Restaurer**.

## Tests

```bat
python eclatplus.py --selftest
```

Manuel : 50, 100, 150, 200, Restaurer, Limiter au pilote à 150 (Loupe OFF), jeu fenêtré / borderless / plein écran exclusif.

## Comparaison avant / après

| | Ancien (C# / WinForms / .NET 8) | Nouveau (Python stdlib) |
|---|---|---|
| Au repos | Runtime CLR + UI custom + Loupe souvent allumée | `mainloop` bloquant, Loupe **éteinte** si ≤ 100 |
| RAM | souvent 60–120 Mo | `pythonw` ~ 20–40 Mo ; exe one-file davantage |
| CPU idle | timers / Loupe DWM | ~ 0 % |
| Extra éclat | Loupe dès **> 50** | Loupe seulement **> 100** |
| Mises à jour | Releases GitHub | `version.json` sur le dépôt, zip de `main` |
| Capture / overlay | non | non |

Le gain FPS vient surtout de **ne plus laisser Magnification.dll initialisée** pendant que tu joues en 0–100.

## Limitations

- Plein écran **exclusif** : DWM n’applique souvent pas la couche extra. Le pilote 0–100 continue de marcher. Passe en borderless pour > 100.
- Intel / GPU sans DVC : 0–100 ne fait rien ; > 100 peut encore utiliser la Loupe.
- La Loupe > 100 a un coût DWM (Windows, pas Python). Mode **Limiter au pilote** pour les jeux compétitifs.
- Pas de jolie UI, volontairement.
