import csv
import subprocess
from pathlib import Path
from typing import Optional

import typer
from loguru import logger

app = typer.Typer()

def calculate_seconds(minutes: int, seconds: int) -> int:
    """Convertit minutes et secondes en secondes totales."""
    return minutes * 60 + seconds

@app.command()
def main(
    csv_path: Path = typer.Argument(..., help="Chemin vers le fichier CSV d'entrée."),
    output_path: Optional[Path] = typer.Option(None, "--output", "-o", help="Chemin vers le fichier de sortie pour les commandes ffmpeg."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Si activé, ne génère que les commandes sans écrire ni exécuter."),
    execute: bool = typer.Option(False, "--execute", help="Si activé, exécute directement les commandes ffmpeg générées. Attention !")
):
    """
    Génère et/ou exécute des commandes ffmpeg à partir d'un fichier CSV contenant des timestamps de découpe vidéo.
    """
    logger.info(f"Lecture du fichier CSV : {csv_path}")

    with open(csv_path, mode='r') as csvfile:
        reader = csv.DictReader(csvfile)
        commands = []
        for row in reader:
            try:
                start_seconds = calculate_seconds(int(row['debutM']), int(row['debutS']))
                end_seconds = calculate_seconds(int(row['finM']), int(row['finS']))
                duration_seconds = end_seconds - start_seconds

                command = (
                    f"ffmpeg -i {row['fsource']} -c:a copy -c:v copy "
                    f"-ss {start_seconds} -t {duration_seconds} {row['fdest']}"
                )
                commands.append(command)
                logger.info(f"Commande générée : {command}")
            except KeyError as e:
                logger.error(f"Colonne manquante dans le CSV : {e}")
                raise typer.Exit(1)
            except Exception as e:
                logger.error(f"Erreur lors du traitement de la ligne : {e}")
                raise typer.Exit(1)

    # Écriture des commandes dans un fichier si demandé
    if output_path and not dry_run:
        with open(output_path, 'w') as f:
            f.write("\n".join(commands))
        logger.success(f"Commandes enregistrées dans : {output_path}")

    # Exécution des commandes si demandé
    if execute:
        if not dry_run:
            logger.warning("Attention : vous allez exécuter les commandes ffmpeg suivantes :")
            for cmd in commands:
                print(f"  - {cmd}")
            confirm = typer.confirm("Confirmez-vous l'exécution ?")
            if not confirm:
                logger.info("Exécution annulée.")
                raise typer.Abort()
            for cmd in commands:
                logger.info(f"Exécution : {cmd}")
                subprocess.run(cmd, shell=True, check=True)
                logger.success(f"Commande exécutée avec succès : {cmd}")
        else:
            logger.warning("--execute ignoré en mode --dry-run.")

    # Affichage à l'écran si aucun fichier de sortie ni exécution
    if not output_path and not execute and not dry_run:
        logger.info("Commandes ffmpeg générées :")
        for cmd in commands:
            print(cmd)

if __name__ == "__main__":
    app()
