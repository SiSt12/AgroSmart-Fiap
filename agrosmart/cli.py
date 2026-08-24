"""Interface de linha de comando do AgroSmart.

    python -m agrosmart.cli gerar-dados
    python -m agrosmart.cli treinar
    python -m agrosmart.cli classificar --input data/samples --out outputs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import CLASSES
from .dataset import listar_imagens
from .export import build_row, export_results
from .features import imread_unicode
from .model import (
    DATA_TRAIN,
    METRICS_PATH,
    MODEL_PATH,
    load_metrics,
    load_model,
    predict,
    train,
)
from .synthetic import generate_dataset

RAIZ = Path(__file__).resolve().parent.parent


def cmd_gerar_dados(args: argparse.Namespace) -> int:
    contagem = generate_dataset(args.out, n_per_class=args.n, seed=args.seed)
    print(f"Dataset simulado gerado em {Path(args.out).resolve()}")
    for classe, total in contagem.items():
        print(f"  {classe}: {total} imagens")

    # Algumas copias soltas para testar upload no app sem mexer no treino.
    amostras = Path(args.samples)
    amostras.mkdir(parents=True, exist_ok=True)
    for classe in CLASSES:
        for origem in listar_imagens(Path(args.out) / classe)[:3]:
            (amostras / f"amostra_{origem.name}").write_bytes(origem.read_bytes())
    print(f"Amostras para teste manual em {amostras.resolve()}")
    return 0


def cmd_treinar(args: argparse.Namespace) -> int:
    metricas = train(data_root=args.data, model_path=args.model,
                     metrics_path=args.metrics, seed=args.seed)
    print("Treino concluido.")
    print(f"  imagens ............ {metricas['total_imagens']} "
          f"({metricas['imagens_por_classe']})")
    print(f"  acuracia (holdout) . {metricas['acuracia_holdout']:.2%} "
          f"em {metricas['imagens_teste']} imagens de teste")
    if metricas["cross_val_media"] is not None:
        print(f"  cross-val ({metricas['cross_val_folds']} folds) "
              f"{metricas['cross_val_media']:.2%} "
              f"+/- {metricas['cross_val_desvio']:.2%}")
    print(f"  matriz de confusao . {metricas['matriz_confusao']['valores']} "
          f"(ordem: {metricas['matriz_confusao']['classes']})")
    print(f"  modelo salvo em .... {metricas['arquivo_modelo']}")
    return 0


def cmd_classificar(args: argparse.Namespace) -> int:
    entrada = Path(args.input)
    imagens = listar_imagens(entrada) if entrada.is_dir() else [entrada]
    if not imagens:
        print(f"Nenhuma imagem encontrada em {entrada}", file=sys.stderr)
        return 1

    modelo = load_model(args.model)
    linhas = []
    for caminho in imagens:
        resultado = predict(modelo, imread_unicode(str(caminho)))
        linhas.append(build_row(caminho.name, resultado))
        print(f"{caminho.name:<32} {resultado['categoria']:<10} "
              f"{resultado['confianca']:.2%}")

    destinos = export_results(linhas, args.out, args.basename,
                              load_metrics(args.metrics))
    print(f"\n{len(linhas)} imagens classificadas.")
    print(f"  CSV  -> {destinos['csv']}")
    print(f"  JSON -> {destinos['json']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agrosmart",
        description="Prototipo de visao computacional para triagem de folhas.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p_gerar = sub.add_parser("gerar-dados", help="gera o dataset simulado")
    p_gerar.add_argument("--out", default=str(DATA_TRAIN))
    p_gerar.add_argument("--samples", default=str(RAIZ / "data" / "samples"))
    p_gerar.add_argument("-n", type=int, default=30, help="imagens por classe")
    p_gerar.add_argument("--seed", type=int, default=42)
    p_gerar.set_defaults(func=cmd_gerar_dados)

    p_treinar = sub.add_parser("treinar", help="treina e salva o classificador")
    p_treinar.add_argument("--data", default=str(DATA_TRAIN))
    p_treinar.add_argument("--model", default=str(MODEL_PATH))
    p_treinar.add_argument("--metrics", default=str(METRICS_PATH))
    p_treinar.add_argument("--seed", type=int, default=42)
    p_treinar.set_defaults(func=cmd_treinar)

    p_class = sub.add_parser("classificar", help="classifica uma imagem ou pasta")
    p_class.add_argument("--input", required=True, help="arquivo ou pasta")
    p_class.add_argument("--out", default=str(RAIZ / "outputs"))
    p_class.add_argument("--basename", default=None)
    p_class.add_argument("--model", default=str(MODEL_PATH))
    p_class.add_argument("--metrics", default=str(METRICS_PATH))
    p_class.set_defaults(func=cmd_classificar)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
