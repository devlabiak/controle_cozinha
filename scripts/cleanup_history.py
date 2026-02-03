"""Remove movimentações de estoque com mais de 90 dias.

Execute regularmente (ex.: via cron) para manter apenas 90 dias de histórico.
"""

from app.services.history_cleanup import cleanup_history, RETENTION_DAYS


def main():
    removed = cleanup_history()
    print(f"🧹 Histórico limpo: {removed} movimentações removidas (>{RETENTION_DAYS} dias)")


if __name__ == "__main__":
    main()
