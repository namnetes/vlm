# Importations de bibliothèques standard
import datetime


class ErrorHandler:
    """
    Classe ErrorHandler pour gérer les messages de log (info, warning, error)
    dans un fichier.

    Cette classe est conçue comme un singleton, c'est-à-dire qu'une seule
    instance sera créée, même si elle est instanciée plusieurs fois. Cela
    permet de centraliser la gestion des erreurs et des logs dans toute
    l'application sans ouvrir plusieurs fois le fichier de log.

    Attributes:
        _instance (ErrorHandler): L'instance unique de la classe.
        log_filename (str): Le nom du fichier où les logs sont enregistrés.
        log_file (file): Le fichier ouvert où les messages de log sont écrits.
    """

    _instance = None  # Stocke l'instance unique de la classe

    def __new__(cls, log_filename):
        """
        Contrôle la création de l'instance unique (singleton).

        Si aucune instance n'a encore été créée, elle est initialisée avec le
        fichier de log spécifié. Sinon, la même instance est retournée.

        Args:
            log_filename (str): Nom du fichier de log à utiliser.

        Returns:
            ErrorHandler: L'instance unique de ErrorHandler.
        """
        if cls._instance is None:
            cls._instance = super(ErrorHandler, cls).__new__(
                cls
            )  # Crée une nouvelle instance
            cls._instance.__init__(log_filename)  # Initialise l'instance
        return cls._instance

    def __init__(self, log_filename):
        """
        Initialise le gestionnaire d'erreurs et ouvre le fichier de log en
        mode ajout.

        Le fichier de log est ouvert en mode 'a' (append), ce qui signifie que
        les nouveaux messages seront ajoutés à la fin du fichier sans effacer
        les précédents.

        Args:
            log_filename (str): Nom du fichier de log à utiliser.
        """
        # Vérifie si le fichier de log a déjà été ouvert pour éviter de le
        # réinitialiser
        if not hasattr(self, "log_file"):
            self.log_filename = log_filename
            try:
                self.log_file = open(self.log_filename, "a")  # Ouvre la log
                self.log_info(
                    "Gestionnaire d'erreurs initialisé."
                )  # Log d'initialisation
            except Exception as e:
                print(f"Erreur lors de l'ouverture du fichier de log: {str(e)}")

    def log_info(self, message):
        """
        Enregistre un message d'information dans le fichier de log.

        Args:
            message (str): Le message à enregistrer dans le log.
        """
        self._log("INFO", message)

    def log_warning(self, message):
        """
        Enregistre un message d'avertissement dans le fichier de log.

        Args:
            message (str): Le message d'avertissement à enregistrer dans
                           le fichier log.
        """
        self._log("WARNING", message)

    def log_error(self, message):
        """
        Enregistre un message d'erreur dans le fichier de log.

        Args:
            message (str): Le message d'erreur à enregistrer dans le log.
        """
        self._log("ERROR", message)

    def _log(self, level, message):
        """
        Écrit un message de log avec un niveau spécifié dans le fichier de log.

        Ce message est horodaté et inclut le niveau (INFO, WARNING, ERROR)
        pour indiquer le type de message.

        Args:
            level (str): Le niveau du message (ex. 'INFO', 'WARNING', 'ERROR').
            message (str): Le message à écrire dans le log.
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {level}: {message}\n"
        try:
            self.log_file.write(log_message)  # Écrit le message dans la log
            self.log_file.flush()  # Assure l'écriture immédiate
        except Exception as e:
            print(f"Erreur lors de l'écriture dans le fichier de log: {str(e)}")

    def __del__(self):
        """
        Ferme le fichier de log lorsque l'instance est détruite.

        Cette méthode est appelée automatiquement lorsque l'instance est
        supprimée, assurant que le fichier de log est correctement fermé.
        """
        if hasattr(self, "log_file"):
            self.log_file.close()
            print(f"Fichier de log '{self.log_filename}' fermé.")
