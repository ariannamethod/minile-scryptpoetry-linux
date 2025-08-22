from dataclasses import dataclass
import os
import pathlib

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        # Fallback если нет tomli - создаем заглушку
        class MockTomllib:
            @staticmethod
            def loads(s):
                return {}
            @staticmethod
            def load(f):
                return {}
        tomllib = MockTomllib()


@dataclass
class Settings:
    """Project configuration settings."""

    n_gram_level: int = 2

    reproduction_interval: int = 3600  # seconds

    def __post_init__(self) -> None:
        # load from pyproject if available
        project = (
            pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
        )
        if project.exists():
            with project.open("rb") as f:
                data = tomllib.load(f)
            n = (
                data.get("tool", {})
                .get("arianna", {})
                .get("n_gram_level", self.n_gram_level)
            )
            self.n_gram_level = int(
                os.getenv(
                    "ARIANNA_NGRAM_LEVEL",
                    os.getenv("ARIANNA_NGRAM_SIZE", n),
                )
            )
            interval = (
                data.get("tool", {})
                .get("arianna", {})
                .get("reproduction_interval", self.reproduction_interval)
            )
            self.reproduction_interval = int(
                os.getenv("ARIANNA_REPRO_INTERVAL", str(interval))
            )
        else:
            self.n_gram_level = int(
                os.getenv(
                    "ARIANNA_NGRAM_LEVEL",
                    os.getenv("ARIANNA_NGRAM_SIZE", self.n_gram_level),
                )
            )

            self.reproduction_interval = int(
                os.getenv(
                    "ARIANNA_REPRO_INTERVAL",
                    str(self.reproduction_interval),
                )
            )


settings = Settings()

# Feature flags controlling optional modules
FEATURES = {
    "skin": True,  # Включаем визуальные мутации!
    "entropy": True,
    "pain": True,
    "sixth_sense": True,
    "hash_monitor": True,
    "bio_evolution": True,
}


def is_enabled(feature_name: str) -> bool:
    """Return ``True`` if ``feature_name`` is enabled."""
    return FEATURES.get(feature_name, False)
