# modulo unreal FALSO: so para importar a matematica do Tools/Player/vela_pega.py fora da Unreal (nada roda na engine)
import os, tempfile


class _Any:
    def __getattr__(self, k): return _Any()
    def __call__(self, *a, **k): return _Any()


class Paths:
    @staticmethod
    def convert_relative_path_to_full(p): return p

    @staticmethod
    def project_saved_dir():
        d = os.path.join(tempfile.gettempdir(), "lux_offline")
        os.makedirs(os.path.join(d, "LuxSnapshots"), exist_ok=True)
        return d


def log(*a): pass


def __getattr__(k): return _Any()
