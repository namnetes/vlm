# Importations de bibliothèques standard
from timeit import default_timer as timer

# Importations de modules locaux
from args_handler import parse_arguments
from error_handler import ErrorHandler
from file_reader import process_file


def main():
    # Parser les arguments
    args = parse_arguments()

    # Initialiser le gestionnaire d'erreurs avec le fichier de log
    error_handler = ErrorHandler(args.log_file)
    error_handler.log_info("Début des traitements...")

    # Traiter le fichier
    process_file(
        args.input_file, args.output_file, args.sep, args.log_file, args.verbose
    )

    return args  # Retourner args pour utilisation dans le bloc principal


if __name__ == "__main__":

    # Mesurer le temps d'exécution
    start_time = timer()

    args = main()  # Appeler main() et récupérer les arguments utilisés

    end_time = timer()
    execution_time = end_time - start_time

    # Utiliser l'instance singleton pour loguer le temps d'exécution
    error_handler = ErrorHandler(args.log_file)

    error_handler.log_info(f"Fin des traitements du fichier {args.input_file}")
    error_handler.log_info(f"Temps d'exécution : {execution_time:.4f} secondes")
