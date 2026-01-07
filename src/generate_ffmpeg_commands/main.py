import csv
import subprocess
from pathlib import Path
from typing import Optional

import typer
from loguru import logger

app = typer.Typer()

def calculate_seconds(minutes: int, seconds: int) -> int:
    """Convertit minutes et secondes en secondes totales."""
    if minutes < 0 or seconds < 0:
        raise ValueError(f"Minutes et secondes doivent être positifs: {minutes}m {seconds}s")
    if seconds >= 60:
        raise ValueError(f"Les secondes doivent être < 60: {seconds}s")
    return minutes * 60 + seconds

@app.command()
def main(
    csv_path: Path = typer.Argument(..., help="Chemin vers le fichier CSV d'entrée."),
    output_path: Optional[Path] = typer.Option(None, "--output", "-o", help="Chemin vers le fichier de sortie pour les commandes ffmpeg."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Si activé, ne génère que les commandes sans écrire ni exécuter."),
    execute: bool = typer.Option(False, "--execute", help="Si activé, exécute directement les commandes ffmpeg générées. Attention !")
) -> None:
    """
    Génère et/ou exécute des commandes ffmpeg à partir d'un fichier CSV contenant des timestamps de découpe vidéo.
    """
    # Vérification de l'existence du fichier CSV
    if not csv_path.exists():
        logger.error(f"Le fichier CSV n'existe pas : {csv_path}")
        raise typer.Exit(1)
    
    logger.info(f"Lecture du fichier CSV : {csv_path}")

    with open(csv_path, mode='r') as csvfile:
        reader = csv.DictReader(csvfile)
        commands = []
        for line_num, row in enumerate(reader, start=2):  # start=2 car ligne 1 = header
            try:
                # Validation des colonnes requises
                required_columns = ['debutM', 'debutS', 'finM', 'finS', 'fsource', 'fdest']
                missing_columns = [col for col in required_columns if col not in row]
                if missing_columns:
                    logger.error(f"Ligne {line_num}: Colonnes manquantes : {missing_columns}")
                    raise typer.Exit(1)
                
                # Validation et conversion des timestamps
                start_seconds = calculate_seconds(int(row['debutM']), int(row['debutS']))
                end_seconds = calculate_seconds(int(row['finM']), int(row['finS']))
                duration_seconds = end_seconds - start_seconds
                
                # Vérification que la durée est positive
                if duration_seconds <= 0:
                    logger.error(
                        f"Ligne {line_num}: La durée doit être positive. "
                        f"Début: {start_seconds}s, Fin: {end_seconds}s"
                    )
                    raise typer.Exit(1)
                
                # Vérification que le fichier source existe
                source_path = Path(row['fsource'])
                if not source_path.exists():
                    logger.error(f"Ligne {line_num}: Le fichier source n'existe pas : {source_path}")
                    raise typer.Exit(1)
                
                # Vérification que le répertoire de destination existe
                dest_path = Path(row['fdest'])
                if not dest_path.parent.exists():
                    logger.error(
                        f"Ligne {line_num}: Le répertoire de destination n'existe pas : {dest_path.parent}"
                    )
                    raise typer.Exit(1)

                command = (
                    f"ffmpeg -i {row['fsource']} -c:a copy -c:v copy "
                    f"-ss {start_seconds} -t {duration_seconds} {row['fdest']}"
                )
                commands.append(command)
                logger.info(f"Commande générée : {command}")
            except KeyError as e:
                logger.error(f"Ligne {line_num}: Colonne manquante dans le CSV : {e}")
                raise typer.Exit(1)
            except ValueError as e:
                logger.error(f"Ligne {line_num}: Erreur de validation : {e}")
                raise typer.Exit(1)
            except Exception as e:
                logger.error(f"Ligne {line_num}: Erreur lors du traitement de la ligne : {e}")
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
            
            for idx, cmd in enumerate(commands, start=1):
                logger.info(f"Exécution ({idx}/{len(commands)}): {cmd}")
                try:
                    # Utilisation de subprocess.run sans shell=True pour éviter l'injection de commandes
                    # On parse la commande pour extraire les arguments
                    cmd_parts = cmd.split()
                    subprocess.run(cmd_parts, check=True, capture_output=True, text=True)
                    logger.success(f"Commande exécutée avec succès : {cmd}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Erreur lors de l'exécution de la commande : {cmd}")
                    logger.error(f"Code de retour : {e.returncode}")
                    logger.error(f"Sortie d'erreur : {e.stderr}")
                    raise typer.Exit(1)
        else:
            logger.warning("--execute ignoré en mode --dry-run.")

    # Affichage à l'écran si aucun fichier de sortie ni exécution
    if not output_path and not execute and not dry_run:
        logger.info("Commandes ffmpeg générées :")
        for cmd in commands:
            print(cmd)

if __name__ == "__main__":
    app()
