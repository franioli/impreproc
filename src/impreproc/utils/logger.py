import logging
from pathlib import Path
from datetime import date, datetime


def setup_logger(
    log_level,
    log_to_file: bool = False,
    base_log_name: str = "log",
    log_dir: Path = None,
) -> None:
    handlers = [logging.StreamHandler()]
    if log_to_file:
        if log_dir is None:
            log_dir = Path("logs")
        else:
            log_dir = Path(log_dir)
        log_dir.mkdir(exist_ok=True)
        today = date.today()
        now = datetime.now()
        current_date = f"{today.strftime('%Y_%m_%d')}_{now.strftime('%H:%M')}"
        log_file = log_dir / f"{base_log_name}_{current_date}.log"
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(filename)s - ln %(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


if __name__ == "__main__":
    setup_logger(logging.INFO)
    logging.info("Hello World!")
