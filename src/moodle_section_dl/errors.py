class MoodleDownloadError(Exception):
    """Erro esperado que pode ser apresentado diretamente no CLI."""


class AuthenticationError(MoodleDownloadError):
    """A autenticação no CAS/Moodle falhou."""


class SectionNotFoundError(MoodleDownloadError):
    """A seção solicitada não existe na página do curso."""
