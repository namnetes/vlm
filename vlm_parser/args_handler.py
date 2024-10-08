# Importations de bibliothèques standard
import argparse
import datetime


def parse_arguments():
    parser = argparse.ArgumentParser(description="Parser Script for VLM Analysis.")

    # Argument pour le fichier d'entrée
    parser.add_argument(
        "-f", "--input_file", required=True, help="Input file to process"
    )

    # Argument pour le fichier de sortie
    parser.add_argument(
        "-o", "--output_file", required=True, help="Output file to write"
    )

    # Argument pour le séparateur du CSV, avec un choix entre "," et ";",
    # et ";" comme valeur par défaut
    parser.add_argument(
        "--sep",
        default=";",
        choices=[",", ";"],
        help="CSV field separator (default: ;)",
    )

    # Argument pour le fichier de log, avec un nom par défaut basé sur la date
    # et l'heure
    default_log_filename = (
        f"vlm_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    parser.add_argument(
        "-l",
        "--log_file",
        default=default_log_filename,
        help=f"Log file name (default: {default_log_filename})",
    )

    # Argument pour activer le mode verbeux
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",  # Utilise store_true pour activer le mode verbeux quand -v est fourni
        default=False,  # Le mode verbeux est désactivé par défaut
        help="Run in verbose mode (default: quiet mode), use -v to log every output message",
    )

    return parser.parse_args()
